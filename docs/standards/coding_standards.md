# Project Coding Standards

## General Principles
- Code readability takes precedence over cleverness
- Follow the principle of least surprise
- Maintain consistent patterns throughout the codebase
- Write code for the maintainer, not just for the computer

## Formatting
- Use 4 spaces for indentation (not tabs)
- Maximum line length of 88 characters
- Use clear, descriptive variable and function names
- Group related code blocks with a single blank line between them
- Use two blank lines between top-level definitions

## Documentation
- All modules should have docstrings explaining their purpose
- Functions should have docstrings describing inputs, outputs, and behavior
- Complex logic should have inline comments explaining the "why" not the "what"
- Keep comments up-to-date with code changes

## Testing
- All features should have unit tests
- Aim for at least 80% test coverage
- Test edge cases and failure modes
- Use descriptive test names that explain the expected behavior

## Language-Specific Guidelines

### Python

#### Style
- Follow PEP 8 style guide with the exceptions noted above
- Use type hints for function parameters and return values
- Use f-strings for string formatting
- Use context managers (`with` statements) for resource management

#### Naming Conventions
- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private attributes/methods: `_leading_underscore`

#### Package Management
- Use requirements.txt or pyproject.toml for dependency management
- Pin dependencies to specific versions or ranges
- Document virtual environment setup in the README

#### Testing
- Use pytest for unit testing
- Organize tests to mirror the structure of the source code
- Use fixtures for test setup and teardown
- Use parametrized tests for testing multiple cases

### JavaScript/TypeScript

#### Style
- Use ES6+ syntax features
- Use const for variables that don't change
- Use let instead of var for variables that do change
- Use async/await rather than Promise chains when possible

#### Naming Conventions
- Functions and variables: `camelCase`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private properties: `_leadingUnderscore`

#### Package Management
- Use package.json for dependency management
- Lock dependencies using package-lock.json or yarn.lock
- Document Node.js version requirements

#### Testing
- Use Jest for unit testing
- Use descriptive test blocks and assertions
- Mock external dependencies
- Separate unit tests from integration tests

### General Code Organization

#### Directory Structure
- Group files by feature rather than by type
- Keep related files close to each other
- Use index files to simplify imports
- Limit directory nesting to 3-4 levels

#### Imports
- Order imports consistently:
  1. Standard library imports
  2. Third-party package imports
  3. Local imports
- Use absolute imports from project root when appropriate
- Avoid circular dependencies

#### Error Handling
- Be specific about the errors you catch
- Provide meaningful error messages
- Log errors appropriately
- Don't swallow exceptions without handling them

#### Security Practices
- Never hardcode sensitive information
- Validate all input, especially user input
- Use established libraries for security-critical functions
- Apply the principle of least privilege

### Code Review Checklist
- Does the code follow the project's style guidelines?
- Is the code well-documented?
- Are there sufficient tests?
- Is error handling comprehensive?
- Is the code efficient and performant?
- Are there any security concerns?
- Is the code maintainable and extensible?