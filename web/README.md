# Image Search Web UI

A modern, locally-hosted web interface for the Image Search system powered by CLIP AI with query enhancement and intelligent reranking.

## Features

- **Intelligent Search**: Search your images using natural language queries
  - Powered by CLIP embeddings
  - Query enhancement using Gemini AI
  - Caption-based reranking with alpha=0.4
  - Configurable number of results (K)

- **Image Upload**: Upload individual images or entire directories
  - Drag-and-drop support
  - Automatic indexing into Pinecone vector database
  - Progress feedback

- **Search History**: Track your recent searches
  - Persistent storage using browser localStorage
  - Quick access to previous queries
  - Click to reload past searches

- **Fixed-Size Collage Layout**: Results in a compact rectangle
  - Up to 8 images displayed in a fixed-size collage (~570px height)
  - No scrolling needed to see initial results
  - Higher-ranked images appear larger
  - "See More" overlay for additional results (shows count)
  - Click to expand to scrollable grid view
  - Modern, responsive design
  - Hover to view image captions and scores

- **Settings Page**: Configure API keys and environment
  - Edit Pinecone configuration
  - Update Gemini API settings
  - Modify CLIP model parameters
  - Test API connections
  - All changes persist to `.env` file

- **Error Handling**: Comprehensive validation
  - API key validation on startup
  - Warnings redirect to settings page
  - Clear error messages

## Quick Start

### 1. Install Dependencies

Make sure you have the required Python packages installed:

```bash
# From the project root directory
pip install -r requirements.txt
```

This will install Flask and all other dependencies.

### 2. Configure API Keys

Ensure your `.env` file in the project root has the required API keys:

```bash
# Required API keys
PINECONE_API_KEY=your_pinecone_api_key
GEMINI_API_KEY=your_gemini_api_key

# Optional: Configure these if different from defaults
INDEX_NAME=img-search-clip-rp-384
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
CLIP_MODEL=sentence-transformers/clip-ViT-B-32
GEMINI_MODEL=gemini-2.0-flash
REDUCE_DIM=384
```

You can also configure these settings from the web UI Settings page after starting the server.

### 3. Start the Web Server

From the `web` directory:

```bash
cd web
python app.py
```

Or from the project root:

```bash
python web/app.py
```

The server will start at `http://localhost:5001`

### 4. Open Your Browser

Navigate to: `http://localhost:5001`

You should see the Image Search interface!

## Usage Guide

### Uploading Images

1. Click the "Upload Images" button or drag and drop images onto the upload area
2. Select one or multiple image files (PNG, JPG, JPEG supported)
3. Images will be automatically uploaded and indexed
4. You'll see a confirmation message when complete
5. The stats counter will update to show total indexed images

### Searching for Images

1. Enter a natural language query in the search bar
   - Examples: "sunset on the beach", "person reading a book", "mountain landscape"
2. Optionally adjust the number of results (K) - default is 15
3. Click "Search" or press Enter
4. Wait for the processing indicator
5. Results will appear in an asymmetric grid layout
6. Hover over images to see:
   - Similarity score
   - AI-generated caption

### Configuration

The search is pre-configured with optimal settings:
- **Mode**: CLIP with caption reranking
- **Alpha**: 0.4 (blend weight for caption similarity)
- **Query Enhancement**: Enabled (uses Gemini to enhance queries)

These settings provide the best balance of speed and accuracy.

### Managing Settings

1. Click the "Settings" button in the sidebar
2. Edit any configuration values:
   - Pinecone API key and index settings
   - Gemini API key and model
   - CLIP model and dimensions
3. Click "Test Connection" to validate your settings
4. Click "Save Settings" to persist changes
5. **Important**: Restart the server for changes to take effect

### Search History

- All searches are automatically saved to your browser's localStorage
- Click any history item to reload that search
- History persists across sessions
- Shows query, number of results, and timestamp

## Architecture

### Backend (Flask API)

Located in `web/app.py`:

- `/` - Main search interface
- `/settings` - Settings page
- `/api/search` - POST: Search for images
- `/api/upload` - POST: Upload and index images
- `/api/settings` - GET/POST: Read/update configuration
- `/api/validate` - GET: Validate API keys
- `/api/stats` - GET: Index statistics
- `/api/image/<path>` - GET: Serve image files

### Frontend

- `templates/index.html` - Main search interface
- `templates/settings.html` - Configuration page
- `static/css/styles.css` - Modern dark theme styling
- `static/js/app.js` - Search and upload functionality
- `static/js/settings.js` - Settings management

### Data Flow

1. **Upload**: Files → Flask → Local storage → Pinecone index
2. **Search**: Query → Enhancement (Gemini) → CLIP embedding → Pinecone search → Caption reranking → Results
3. **Settings**: Form → Flask → `.env` file → Environment reload

## Directory Structure

```
web/
├── app.py                 # Flask application
├── README.md             # This file
├── templates/            # HTML templates
│   ├── index.html       # Main search page
│   └── settings.html    # Settings page
├── static/              # Static assets
│   ├── css/
│   │   └── styles.css   # Stylesheet
│   └── js/
│       ├── app.js       # Main application logic
│       └── settings.js  # Settings page logic
└── uploads/             # Uploaded images storage
```

## Troubleshooting

### "API Configuration Error" on Startup

**Problem**: Missing or invalid API keys

**Solution**:
1. Check your `.env` file in the project root
2. Ensure `PINECONE_API_KEY` and `GEMINI_API_KEY` are set
3. Or click "Go to Settings" and configure them in the UI

### Images Not Loading

**Problem**: Image paths not found

**Solution**:
1. Uploaded images are stored in `web/uploads/`
2. For existing indexed images, ensure the original paths are accessible
3. Check browser console for specific errors

### Search Returns No Results

**Problem**: No images indexed or query doesn't match

**Solution**:
1. Upload some images first using the upload button
2. Check the stats counter shows indexed images
3. Try a different, more general query
4. Verify your Pinecone index exists and has data

### Settings Not Persisting

**Problem**: Changes don't take effect

**Solution**:
1. Ensure you clicked "Save Settings"
2. **Restart the Flask server** (required for env changes)
3. Check file permissions on `.env`

### Port 5001 Already in Use

**Problem**: Another service is using port 5001

**Solution**:
Edit `web/app.py` and change the port in the last line:
```python
app.run(debug=True, host='0.0.0.0', port=5002)  # Changed to 5002
```

**Note**: The default port was changed from 5000 to 5001 to avoid conflicts with macOS AirPlay Receiver.

## Performance Tips

- **Batch Upload**: Upload multiple images at once for faster indexing
- **Optimal K**: Start with K=10-20 for best results
- **Query Enhancement**: Enabled by default, provides better results for short queries
- **Browser Cache**: Search history is stored locally for instant access

## Security Notes

This application is designed for **local use only**:

- Runs on `localhost` by default
- API keys stored in `.env` file
- No external network access required (except API calls to Pinecone/Gemini)
- Uploaded images stored locally in `web/uploads/`

**Do not expose this server to the internet without adding proper authentication!**

## Development

### Modifying the UI

- Edit `templates/*.html` for structure changes
- Edit `static/css/styles.css` for styling
- Edit `static/js/*.js` for functionality

Flask's debug mode auto-reloads on file changes.

### Adding New Features

1. Add API endpoint in `web/app.py`
2. Update frontend JavaScript to call the new endpoint
3. Update templates if UI changes needed

## Support

For issues or questions:
1. Check this README
2. Review error messages in browser console (F12)
3. Check Flask server logs in terminal
4. Verify API keys are valid

## License

Same as the main Image Search project.
