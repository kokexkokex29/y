# Overview

The Football Club Management Discord Bot is a comprehensive bot designed for managing football clubs within Discord servers. It provides a complete suite of tools for administrators to create and manage football clubs, players, transfers, and matches. The bot uses slash commands exclusively and requires administrator permissions for all management operations. The system includes advanced features like automatic match notifications, financial tracking, player valuations, and comprehensive statistics.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
The application is built using discord.py with a focus on slash commands and asynchronous operations. The bot implements proper rate limiting protection and error handling to prevent Discord API issues. All commands are restricted to users with administrator permissions for security.

## Database Design
The system uses SQLite as the primary database with a custom Database class managing all operations. The schema includes tables for clubs, players, transfers, matches, and statistics. The database supports multi-guild operations, allowing the bot to work across multiple Discord servers simultaneously.

## Web Server Integration
A Flask web server runs alongside the Discord bot to provide health checks and status monitoring. This dual-architecture approach ensures the bot remains active on hosting platforms and provides external monitoring capabilities.

## Keep-Alive System
A dedicated keep-alive mechanism prevents the bot from sleeping on hosting platforms like render.com. The system includes threaded background processes that ping the web server at regular intervals to maintain uptime.

## Media and Embeds
The bot supports rich Discord embeds with image uploading capabilities from albums. Custom embed formatting is implemented for enhanced visual presentation of club statistics, player information, and match details.

## Background Tasks
Automated background tasks handle match reminders and notifications. The system sends direct messages to team members 5 minutes before scheduled matches and maintains match history.

## Security and Rate Limiting
Comprehensive security measures include administrator-only access controls, input validation, and sophisticated rate limiting to prevent API abuse. The bot implements retry mechanisms and proper error handling for robust operation.

# External Dependencies

## Discord API
- discord.py library for bot functionality and slash command implementation
- Discord Gateway API for real-time events and messaging
- Discord REST API for embed creation and file uploads

## Database
- SQLite for local data persistence
- No external database services required

## Web Framework
- Flask for the status web server
- Bootstrap and Font Awesome for web UI components
- Custom CSS for styling and responsive design

## HTTP Client
- aiohttp for asynchronous HTTP requests in keep-alive functionality
- requests library for synchronous web server health checks

## Hosting Platform
- render.com deployment configuration
- Environment variable management for bot tokens and configuration
- Automatic deployment from repository changes

## Python Libraries
- asyncio for asynchronous task management
- logging for comprehensive error tracking and debugging
- datetime for time-based operations and scheduling
- threading for concurrent background processes
- json for data serialization and configuration management