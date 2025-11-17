"""Flask web application for Image Search UI."""

from __future__ import annotations
import os
import sys
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.imagesearch import index
from src.imagesearch.embeddings import file_id
from src.imagesearch.caption import describe_image, get_cached, put_cached
from src.imagesearch.rerank import rerank_by_caption
from src.imagesearch.enhance import enhance_query
from src.imagesearch.config import PROJECT_ROOT

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def _get_caption_cached(path: str) -> str:
    """Get caption for an image, using cache when available."""
    key = file_id(path)
    cap = get_cached(key)
    if cap:
        return cap

    cap, _ = describe_image(path)
    put_cached(key, cap)
    return cap


@app.route('/')
def index_page():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/settings')
def settings_page():
    """Serve the settings page."""
    return render_template('settings.html')


@app.route('/api/validate', methods=['GET'])
def validate_api_keys():
    """Validate API keys and configuration."""
    errors = []

    # Check Pinecone API key
    if not os.getenv('PINECONE_API_KEY'):
        errors.append('PINECONE_API_KEY not configured')
    else:
        try:
            # Try to get index stats
            index.stats()
        except Exception as e:
            errors.append(f'Pinecone error: {str(e)}')

    # Check Gemini API key
    if not os.getenv('GEMINI_API_KEY'):
        errors.append('GEMINI_API_KEY not configured')
    else:
        try:
            # Try to enhance a test query
            enhance_query('test')
        except Exception as e:
            errors.append(f'Gemini error: {str(e)}')

    if errors:
        return jsonify({'valid': False, 'errors': errors}), 400

    return jsonify({'valid': True, 'message': 'All API keys are valid'})


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current environment settings."""
    env_path = PROJECT_ROOT / '.env'

    if not env_path.exists():
        return jsonify({'error': '.env file not found'}), 404

    settings = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                settings[key] = value

    return jsonify(settings)


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update environment settings."""
    data = request.json
    env_path = PROJECT_ROOT / '.env'

    try:
        # Read existing env file
        existing_lines = []
        if env_path.exists():
            with open(env_path, 'r') as f:
                existing_lines = f.readlines()

        # Update values
        updated_keys = set()
        new_lines = []

        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=', 1)[0]
                if key in data:
                    new_lines.append(f'{key}={data[key]}\n')
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Add new keys
        for key, value in data.items():
            if key not in updated_keys:
                new_lines.append(f'{key}={value}\n')

        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)

        # Reload environment variables
        from dotenv import load_dotenv
        load_dotenv(override=True)

        return jsonify({'success': True, 'message': 'Settings updated successfully'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload images and insert them into the index."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected'}), 400

    uploaded_paths = []
    errors = []

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = app.config['UPLOAD_FOLDER'] / filename

                # Save file
                file.save(str(filepath))
                uploaded_paths.append(str(filepath))

            except Exception as e:
                errors.append(f'{file.filename}: {str(e)}')
        elif file and file.filename:
            errors.append(f'{file.filename}: Invalid file type')

    if not uploaded_paths:
        return jsonify({'error': 'No valid images uploaded', 'details': errors}), 400

    # Insert images into index
    inserted = 0
    insertion_errors = []

    for path in uploaded_paths:
        try:
            index.upsert_one(path)
            inserted += 1
        except Exception as e:
            insertion_errors.append(f'{os.path.basename(path)}: {str(e)}')

    result = {
        'success': True,
        'uploaded': len(uploaded_paths),
        'inserted': inserted,
    }

    if errors or insertion_errors:
        result['warnings'] = errors + insertion_errors

    return jsonify(result)


@app.route('/api/search', methods=['POST'])
def search():
    """Search for images matching a query."""
    data = request.json

    query = data.get('query', '').strip()
    top_k = data.get('top_k', 10)
    alpha = data.get('alpha', 0.4)
    use_enhance = data.get('enhance', True)

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    try:
        # Enhance query if requested
        used_query = query
        if use_enhance:
            try:
                used_query = enhance_query(query)
            except Exception as e:
                # Fall back to original query if enhancement fails
                print(f'Query enhancement failed: {e}')
                used_query = query

        # Fetch 3x results for reranking
        fetch_k = max(1, top_k * 3)
        matches = index.search(used_query, fetch_k)

        if not matches:
            return jsonify({
                'results': [],
                'query': query,
                'enhanced_query': used_query if use_enhance else None,
                'total': 0
            })

        # Rerank by caption similarity
        reranked = rerank_by_caption(
            used_query,
            matches,
            _get_caption_cached,
            alpha=alpha,
            use_blend=True
        )

        # Take top K results
        results = reranked[:top_k]

        # Format results for frontend
        formatted_results = []
        for r in results:
            formatted_results.append({
                'path': r['path'],
                'score': r['final_score'],
                'caption': r['caption'],
                'id': r['id']
            })

        return jsonify({
            'results': formatted_results,
            'query': query,
            'enhanced_query': used_query if use_enhance else None,
            'total': len(formatted_results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/image/<path:filename>')
def serve_image(filename):
    """Serve uploaded images."""
    upload_dir = app.config['UPLOAD_FOLDER']

    # Handle both relative and absolute paths
    # If path doesn't start with /, it might have been stripped by the redirect
    if not filename.startswith('/') and not filename.startswith('Users'):
        # Assume it's a filename in uploads directory
        file_path = upload_dir / filename
        if file_path.exists():
            return send_from_directory(upload_dir, filename)

    # Try as absolute path (add leading / if missing but path looks absolute)
    if filename.startswith('Users/'):
        filename = '/' + filename

    requested_path = Path(filename)

    # Security: ensure the file is in uploads directory
    if upload_dir in requested_path.parents or requested_path.parent == upload_dir:
        return send_from_directory(upload_dir, requested_path.name)

    # If not in uploads, try to serve from absolute path (for existing indexed images)
    if requested_path.exists() and requested_path.is_file():
        return send_from_directory(requested_path.parent, requested_path.name)

    return jsonify({'error': 'Image not found'}), 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get index statistics."""
    try:
        stats = index.stats()
        return jsonify({
            'total_images': stats.get('total_vector_count', 0),
            'dimension': stats.get('dimension', 'N/A'),
            'index_name': index._name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('\n' + '='*60)
    print('Image Search Web UI')
    print('='*60)
    print('\nStarting server at http://localhost:5001')
    print('\nPress Ctrl+C to stop the server\n')

    app.run(debug=True, host='0.0.0.0', port=5001)
