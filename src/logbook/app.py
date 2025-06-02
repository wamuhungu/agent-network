"""
Logbook Application - Personal Note Taking System

A Flask-based web application for creating and managing timestamped text notes
with support for voice recordings and chronological display.
"""

import os
import json
import sqlite3
import base64
from datetime import datetime
from typing import List, Dict, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'logbook-secret-key-change-in-production'

# Add custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to HTML <br> tags."""
    if text is None:
        return ''
    return text.replace('\n', '<br>\n')

# Configuration
DATA_DIR = Path(__file__).parent / 'data'
DB_PATH = DATA_DIR / 'logbook.db'

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


class LogbookEntry:
    """Represents a single logbook entry with text and/or voice content."""
    
    def __init__(self, entry_id: Optional[int] = None, title: str = "", 
                 content: str = "", voice_data: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        """
        Initialize a logbook entry.
        
        Args:
            entry_id: Unique entry identifier
            title: Entry title
            content: Text content
            voice_data: Base64 encoded voice recording
            created_at: Creation timestamp
        """
        self.entry_id = entry_id
        self.title = title
        self.content = content
        self.voice_data = voice_data
        self.created_at = created_at or datetime.now()
    
    @property
    def id(self):
        """Alias for entry_id to maintain compatibility with templates."""
        return self.entry_id
    
    @property
    def formatted_date(self):
        """Format the creation date for display."""
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
    
    def to_dict(self) -> Dict:
        """Convert entry to dictionary format."""
        return {
            'id': self.entry_id,
            'title': self.title,
            'content': self.content,
            'voice_data': self.voice_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'formatted_date': self.formatted_date
        }


class LogbookDatabase:
    """Database manager for logbook entries."""
    
    def __init__(self, db_path: Path):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    voice_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def add_entry(self, entry: LogbookEntry) -> int:
        """
        Add a new entry to the database.
        
        Args:
            entry: LogbookEntry instance to add
            
        Returns:
            ID of the created entry
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO entries (title, content, voice_data, created_at)
                VALUES (?, ?, ?, ?)
            ''', (entry.title, entry.content, entry.voice_data, entry.created_at))
            conn.commit()
            return cursor.lastrowid
    
    def get_all_entries(self, limit: Optional[int] = None) -> List[LogbookEntry]:
        """
        Retrieve all entries in chronological order (newest first).
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of LogbookEntry instances
        """
        query = 'SELECT id, title, content, voice_data, created_at FROM entries ORDER BY created_at DESC'
        if limit:
            query += f' LIMIT {limit}'
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query)
            
            entries = []
            for row in cursor.fetchall():
                # Parse datetime - handle both ISO format and SQLite TIMESTAMP format
                created_at_str = row['created_at']
                try:
                    if 'T' in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                except (ValueError, AttributeError):
                    created_at = datetime.now()
                
                entry = LogbookEntry(
                    entry_id=row['id'],
                    title=row['title'],
                    content=row['content'],
                    voice_data=row['voice_data'],
                    created_at=created_at
                )
                entries.append(entry)
            
            return entries
    
    def get_entry_by_id(self, entry_id: int) -> Optional[LogbookEntry]:
        """
        Retrieve a specific entry by ID.
        
        Args:
            entry_id: Entry ID to retrieve
            
        Returns:
            LogbookEntry instance or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT id, title, content, voice_data, created_at FROM entries WHERE id = ?',
                (entry_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Parse datetime - handle both ISO format and SQLite TIMESTAMP format
                created_at_str = row['created_at']
                try:
                    if 'T' in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                except (ValueError, AttributeError):
                    created_at = datetime.now()
                
                return LogbookEntry(
                    entry_id=row['id'],
                    title=row['title'],
                    content=row['content'],
                    voice_data=row['voice_data'],
                    created_at=created_at
                )
            return None
    
    def delete_entry(self, entry_id: int) -> bool:
        """
        Delete an entry by ID.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
            conn.commit()
            return cursor.rowcount > 0


# Initialize database
db = LogbookDatabase(DB_PATH)


@app.route('/')
def index():
    """Display the main logbook page with all entries."""
    entries = db.get_all_entries(limit=50)  # Limit to latest 50 entries
    # Convert entries to dictionaries for JSON serialization in template
    entries_data = [entry.to_dict() for entry in entries]
    return render_template('index.html', entries=entries, entries_data=entries_data)


@app.route('/add', methods=['GET', 'POST'])
def add_entry():
    """Add a new logbook entry."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        voice_data = request.form.get('voice_data', '').strip()
        
        # Validate input
        if not title and not content:
            return jsonify({'error': 'Either title or content is required'}), 400
        
        # Create entry
        entry = LogbookEntry(
            title=title or f"Entry {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            content=content,
            voice_data=voice_data if voice_data else None
        )
        
        # Save to database
        entry_id = db.add_entry(entry)
        
        if request.is_json:
            return jsonify({
                'success': True,
                'entry_id': entry_id,
                'message': 'Entry added successfully'
            })
        else:
            return redirect(url_for('index'))
    
    return render_template('add_entry.html')


@app.route('/api/entries')
def api_entries():
    """API endpoint to get all entries as JSON."""
    entries = db.get_all_entries(limit=100)
    return jsonify({
        'entries': [entry.to_dict() for entry in entries],
        'total': len(entries)
    })


@app.route('/api/entries/<int:entry_id>')
def api_entry(entry_id: int):
    """API endpoint to get a specific entry by ID."""
    entry = db.get_entry_by_id(entry_id)
    if entry:
        return jsonify(entry.to_dict())
    return jsonify({'error': 'Entry not found'}), 404


@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def api_delete_entry(entry_id: int):
    """API endpoint to delete an entry."""
    if db.delete_entry(entry_id):
        return jsonify({'success': True, 'message': 'Entry deleted'})
    return jsonify({'error': 'Entry not found'}), 404


@app.route('/entry/<int:entry_id>')
def view_entry(entry_id: int):
    """View a specific entry."""
    entry = db.get_entry_by_id(entry_id)
    if entry:
        return render_template('view_entry.html', entry=entry)
    return "Entry not found", 404


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected',
        'total_entries': len(db.get_all_entries())
    })


if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Run the application
    app.run(host='0.0.0.0', port=5001, debug=True)