# Personal Logbook Application

A Flask-based web application for creating and managing timestamped text notes with voice recording capabilities.

## Features

### Core Functionality
- **Text Entries**: Create timestamped text notes with titles and content
- **Voice Recordings**: Record audio notes directly in the browser
- **Chronological Display**: View all entries ordered by creation time (newest first)
- **Search & Filter**: Find entries by title or content
- **Export/Import**: Export entries as JSON for backup

### Voice Recording Features
- **Browser-based Recording**: Record audio directly in supported browsers
- **Multiple Formats**: Supports WebM, WAV, and MP3 audio formats
- **Playback Controls**: Play recordings directly in the interface
- **Download Support**: Download voice recordings as audio files
- **Storage**: Voice data stored as base64 in the database

### User Interface
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Bootstrap Styling**: Modern, clean interface with Bootstrap 5
- **Interactive Elements**: Hover effects, animations, and transitions
- **Accessibility**: Keyboard navigation and screen reader support
- **Auto-save**: Form data automatically saved as you type

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- Modern web browser (Chrome, Firefox, or Safari for voice recording)

### Quick Start

1. **Navigate to the logbook directory**:
   ```bash
   cd src/logbook
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Access the application**:
   Open your browser to `http://localhost:5001`

### Database Setup
The application automatically creates a SQLite database (`data/logbook.db`) on first run.

## Usage Guide

### Creating Text Entries

1. **Navigate to "Add Entry"** from the main page or navigation
2. **Enter a title** (optional - will auto-generate if left blank)
3. **Write your content** in the text area
4. **Click "Save Entry"** to create the entry

### Recording Voice Notes

1. **Go to "Add Entry"** page
2. **Click "Start Recording"** to begin audio capture
3. **Speak your message** (recording timer will show elapsed time)
4. **Click "Stop Recording"** when finished
5. **Preview the recording** using the audio controls
6. **Save the entry** to store both text and audio

### Viewing Entries

- **Home Page**: Shows all entries in chronological order (newest first)
- **Entry Cards**: Display title, content preview, creation time, and voice indicator
- **Full View**: Click "View" to see complete entry with full text and audio playback
- **Statistics**: View total entries, voice recordings count, and active days

### Managing Entries

- **Delete**: Remove entries using the delete button (confirmation required)
- **Export**: Download all entries as JSON file for backup
- **Search**: Use browser's find feature or implement client-side search

## API Endpoints

The application provides REST API endpoints for programmatic access:

### GET /api/entries
Returns all entries as JSON:
```json
{
  "entries": [
    {
      "id": 1,
      "title": "My First Entry",
      "content": "This is my first logbook entry",
      "voice_data": "base64_encoded_audio_data",
      "created_at": "2025-06-01T10:30:00",
      "formatted_date": "2025-06-01 10:30:00"
    }
  ],
  "total": 1
}
```

### GET /api/entries/{id}
Returns a specific entry by ID.

### DELETE /api/entries/{id}
Deletes an entry by ID.

### GET /health
Returns application health status.

## File Structure

```
src/logbook/
├── app.py                 # Main Flask application
├── data/                  # SQLite database storage
│   └── logbook.db        # Auto-created database
├── static/               # Static assets
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       └── main.js       # JavaScript functionality
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Home page
│   ├── add_entry.html    # Add entry form
│   └── view_entry.html   # Entry detail view
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Database Schema

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    voice_data TEXT,          -- Base64 encoded audio
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Browser Compatibility

### Voice Recording Support
- **Chrome**: Full support (WebM format)
- **Firefox**: Full support (WebM format)
- **Safari**: Full support (MP4/AAC format)
- **Edge**: Full support (WebM format)
- **Mobile browsers**: Limited support (iOS Safari works, Android Chrome works)

### Fallback Behavior
If voice recording is not supported, the interface gracefully degrades to text-only mode.

## Configuration

### Application Settings
Edit `app.py` to modify:
- **Port**: Change `port=5001` in the `app.run()` call
- **Host**: Change `host='0.0.0.0'` to restrict access
- **Debug mode**: Set `debug=False` for production
- **Database path**: Modify `DB_PATH` variable

### Security Considerations
- **Secret Key**: Change `app.secret_key` for production use
- **File Upload**: Voice data is stored as base64 in database (no file uploads)
- **Input Validation**: All user inputs are escaped and validated
- **SQLite**: Database is stored locally with no external connections

## Development

### Running in Development Mode
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

### Testing
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests (when implemented)
pytest
```

### Adding Features

1. **New Routes**: Add to `app.py` following Flask conventions
2. **Templates**: Create new HTML files in `templates/`
3. **Styles**: Add CSS to `static/css/style.css`
4. **JavaScript**: Add functionality to `static/js/main.js`

## Deployment

### Production Deployment with Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

### Environment Variables
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
```

### Nginx Configuration Example
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Common Issues

1. **Voice recording not working**:
   - Check browser compatibility
   - Ensure microphone permissions are granted
   - Try a different browser (Chrome recommended)

2. **Database errors**:
   - Ensure `data/` directory is writable
   - Check SQLite is available (included with Python)

3. **Port already in use**:
   - Change port in `app.py` or kill existing process
   - Use `lsof -i :5001` to find process using port 5001

4. **Static files not loading**:
   - Ensure Flask can find static files
   - Check file permissions
   - Clear browser cache

### Debug Mode
Run with debug enabled to see detailed error messages:
```bash
python app.py  # Debug is enabled by default in the code
```

## License

This project is part of the Agent Network system and follows the project's licensing terms.

## Contributing

When contributing to this logbook application:
1. Follow the coding standards in `docs/standards/coding_standards.md`
2. Add tests for new functionality
3. Update this README for new features
4. Ensure responsive design compatibility