import argparse
import torch
import pickle
from flask import Flask, render_template
from flask import request, jsonify, send_from_directory, url_for
from flask_cors import CORS
import os, logging
from text_search import TextSearchModel
from image_search import ImageSearchModel
from video_search import VideoSearchModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize arguments
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=7777)
parser.add_argument('--mode', type=str, default='local')
parser.add_argument('--client_id', type=str, required=True)
parser.add_argument('--client_secret', type=str, required=True)
parser.add_argument('--pickle_path', type=str, default='./embeddings.pkl')
args = parser.parse_args()

app = Flask(__name__)
CORS(app)

# Load the pickle file
with open(args.pickle_path, "rb") as file:
    pickle = pickle.load(file)

# Load the TextSearchModel, ImageSearchModel, and VideoSearchModel
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device: {device}")
logger.info(f"Loading TextSearchModel...")
text_search_model = TextSearchModel(args.pickle_path, './static/images', device=device, 
                                    client_id=args.client_id, client_secret=args.client_secret)

logger.info(f"Loading ImageSearchModel...")
image_search_model = ImageSearchModel(args.pickle_path, './static/images', device=device,
                                      client_id=args.client_id, client_secret=args.client_secret)

logger.info(f"Loading VideoSearchModel...")
video_search_model = VideoSearchModel(args.pickle_path, './static/images', device=device,
                                      client_id=args.client_id, client_secret=args.client_secret)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/page2')
def page2():
    return '<h1>Welcome to Page 2!</h1>'

@app.route('/recommend', methods=['POST'])
def recommend():
    # Get user preferences from the request
    data = request.json
    user_preferences = data['userPreferences']

    # Get recommended image filename from the user preferences
    recommended_image_filename = 'images/1.png'

    # Get the URL of the recommended image
    image_url = url_for('static', filename=recommended_image_filename)

    # Return the recommended image URL as a JSON response
    return jsonify(imageUrl=image_url)

@app.route('/textSearch', methods=['POST'])
def text_search():
    # Get the query text from the request
    data = request.json
    query_text = data['searchText']

    # Use TextSearchModel to get the search result  
    search_result = text_search_model.search(query_text) # ['./images/000000.jpg', ...]

    # Generate image urls
    image_url = []
    for path in search_result:
        image_url.append(url_for('static', filename=path))
    # for idx, id in search_result.items():
    #     img_path = os.path.join('./Modeling/images', f"{id}.jpg")
    #     image_url.append(url_for('static', filename=img_path))
        
    # Generate product information
    results = {}
    results['searchText'] = query_text
    results['searchImage'] = ""
    results['products'] = []
    
    for result in search_result:
        image_name = result.split('/')[-1].split('.')[0]
        product = pickle[image_name]
        results['products'].append({
            'productID': image_name,
            'productName': product['title'],
            'productImage': url_for('static', filename=result),
            'productBigcat': product['big_category'],
            'productSmallcat': product['small_category'],
            'productHashtag': product['item_hashtags']
        })

    return jsonify(results)


@app.route('/imageSearch', methods=['POST'])
def image_search():
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    image = request.files['image']
    prompt = request.form['description']

    # Save the image to the disk
    # First, remove the existing image file
    if os.path.exists('static/uploaded_image.jpg'):
        os.remove('static/uploaded_image.jpg')
    image.save('static/uploaded_image.jpg')

    # Use ImageSearchModel to segment and get top-k image file paths
    search_result = image_search_model.search('static/uploaded_image.jpg', prompt)

    # Generate image urls
    image_url = []
    for path in search_result:
        image_url.append(url_for('static', filename=path))
        
    # Generate product information
    results = {}
    results['searchText'] = prompt
    results['searchImage'] = ""
    results['products'] = []
    
    for result in search_result:
        image_name = result.split('/')[-1].split('.')[0]
        product = pickle[image_name]
        results['products'].append({
            'productID': image_name,
            'productName': product['title'],
            'productImage': url_for('static', filename=result),
            'productBigcat': product['big_category'],
            'productSmallcat': product['small_category'],
            'productHashtag': product['item_hashtags']
        })

    return jsonify(results)

@app.route('/searchMoments', methods=['POST'])
def search_moments():
    # Get the query text from the request
    data = request.json
    video_url = data['videoUrl']
    prompt = data['prompt']

    # Use VideoSearchModel to get top-k moments from the video
    search_result = video_search_model.search_moments(video_url, prompt, top_k=5)

    # Generate image urls
    visualization_url = url_for('static', filename='visualization.jpg')
    image1_url = url_for('static', filename='0.jpg')
    image2_url = url_for('static', filename='1.jpg')
    image3_url = url_for('static', filename='2.jpg')
    image4_url = url_for('static', filename='3.jpg')
    image5_url = url_for('static', filename='4.jpg')

    results = {}
    results['visualization'] = visualization_url
    results['selectedMoments'] = [
        {'image': image1_url},
        {'image': image2_url},
        {'image': image3_url},
        {'image': image4_url},
        {'image': image5_url},
    ]

    return jsonify(results)

@app.route('/videoSearch', methods=['POST'])
def video_search():
    data = request.json
    selected_moment = data['selectedMoment'] # integer index of the selected moment (0-4)
    prompt = data['prompt']

    # First, remove the existing image file
    if os.path.exists('static/uploaded_image.jpg'):
        os.remove('static/uploaded_image.jpg')
    
    original_path = f"./static/{selected_moment}.jpg"
    new_path = f"./static/uploaded_image.jpg"
    os.rename(original_path, new_path)

    # Use ImageSearchModel to segment and get top-k image file paths
    search_result = image_search_model.search('static/uploaded_image.jpg', prompt)

    # Generate image urls
    image_url = []
    for path in search_result:
        image_url.append(url_for('static', filename=path))
    
    # Generate product information
    results = {}
    results['searchText'] = prompt
    results['searchImage'] = ""
    results['products'] = []
    
    for result in search_result:
        image_name = result.split('/')[-1].split('.')[0]
        product = pickle[image_name]
        results['products'].append({
            'productID': image_name,
            'productName': product['title'],
            'productImage': url_for('static', filename=result),
            'productBigcat': product['big_category'],
            'productSmallcat': product['small_category'],
            'productHashtag': product['item_hashtags']
        })

    return jsonify(results)

if __name__ == '__main__':
    if args.mode == 'local':
        app.run(debug=True)
    else:
        app.run(host='0.0.0.0', port=args.port)