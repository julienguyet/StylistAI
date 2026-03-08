from fastmcp import FastMCP
import requests
from pymongo import MongoClient
from dotenv import dotenv_values
import geopy.distance
from bson.objectid import ObjectId
from functools import lru_cache
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
import httpx
import traceback
from qdrant_client import AsyncQdrantClient
import os

env_path = os.path.join(os.path.dirname(__file__), '.env')
config = dotenv_values(env_path)

RECOMMENDER_URL = "http://stylistai-api:8000/invoke"
OLLAMA_URL = "http://ollama:11434/api/embeddings"
QDRANT_URL = "http://qdrant:6333"
COLLECTION_NAME = "fashion_articles"
# GOOGLE_MAPS_API = config['GOOGLE_MAPS_API']
# gmaps = googlemaps.Client(key=GOOGLE_MAPS_API)

_geolocator = Nominatim(user_agent="StylistAI")
_geocode = RateLimiter(
    _geolocator.geocode,
    min_delay_seconds=1.0,
    max_retries=3,
    error_wait_seconds=2.0,
    swallow_exceptions=False
)

mcp = FastMCP("StylistAI")

# Helper function to convert MongoDB documents to JSON-serializable format
def mongo_to_dict(doc):
    """Convert MongoDB document to JSON-serializable dictionary"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [mongo_to_dict(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = mongo_to_dict(value)
            elif isinstance(value, list):
                result[key] = [mongo_to_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result
    return doc

# Helper function to format addresses for geopy tool
def _normalize_address(address: str) -> str:
    return " ".join(address.strip().split())

# Tool to get Recommendations
@mcp.tool
def recommender_tool(customer_id: str, top_k: int = 5,
                    exclude_purchased: bool = True,
                    url: str = "http://stylistai-api:8000/invoke") -> dict:
    """
    Function to call the Stylist API.
    The API retrieves the customer information from Mongo collection
    before submitting data to a Two Tower Tensorflow model.

    This tool should be used when customer ask for new product recommendation.
    
    :param customer_id: id of the customer
    :type customer_id: str
    :param top_k: how many similar items to return
    :type top_k: int
    :param exclude_purchased: Exclude past customer's purchases from recommendations
    :type exclude_purchased: bool
    :param url: url of the recommender API
    :type url: str
    :return: Recommendation results
    :rtype: dict
    """
    try:
        payload = {
            "customer_id": customer_id,
            "top_k": top_k,
            "exclude_purchased": exclude_purchased,
        }

        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result
    except Exception as e:
        return {"error": f"Failed to get recommendations: {str(e)}"}

# Tool to get all cities in db for a given country
@mcp.tool
def get_country_cities(country: str = "Portugal",
                    db: str = "stylistai",
                    collection: str = "stores") -> list:
    """
    A function to check all cities available in stores Mongo DB
    for a given customer country. These list of cities should then be used
    when using function to retrieve nearest stores.

    For example, Lisboa is Lisbon in database.
    
    :param country: Country where live the customer
    :type country: str
    :param db: Mongo DB to use
    :type db: str
    :param collection: Collection to use from Mongo DB
    :type collection: str
    :return: List of cities
    :rtype: list
    """
    try:
        client = MongoClient(config['MONGO_CONNECTION_STRING'])
        db_conn = client[db]
        stores_collection = db_conn[collection]
        results = stores_collection.find({'country': country})
        docs = list(results)
        cities = [doc['city'] for doc in docs]
        return sorted(list(set(cities)))
    except Exception as e:
        return {"error": f"Failed to get cities: {str(e)}"}
    finally:
        client.close()

# Tool to get lat and long. from a customer address
@mcp.tool
#@lru_cache(maxsize=20_000)
def get_customer_coordinates(address: str) -> dict:
    """
    Geocode an address using Nominatim (OpenStreetMap).
    Returns (lat, lon) or None.

    Cached (LRU) to avoid repeated calls in agent flows.
    Rate-limited to respect Nominatim usage.
    """
    coordinates = {}

    addr = _normalize_address(address)
    if not addr:
        return None

    try:
        location = _geocode(addr, exactly_one=True)
        if location is None:
            return None
        coordinates['lat'] = location.latitude
        coordinates['lng'] = location.longitude
        return coordinates

    except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError):
        return None

# get all stores close to customer address
@mcp.tool
def get_near_stores(city: str, db: str = "stylistai", collection: str = "stores") -> list:
    """
    Function to get all stores in a given city in case customer doesn't want
    to disclose its exact address or simply wants to check stores near him when traveling. 
    
    :param city: City where to find stores
    :type city: str
    :param db: Mongo DB to use
    :type db: str
    :param collection: Collection to use from Mongo DB
    :type collection: str
    :return: list of store information dictionaries
    :rtype: list
    """
    try:
        client = MongoClient(config['MONGO_CONNECTION_STRING'])
        db_conn = client[db]
        stores_collection = db_conn[collection]
        docs = stores_collection.find({"$and": [{'country': 'Portugal'}, {'city': city}]})
        
        stores_list = [mongo_to_dict(doc) for doc in docs]
        if not stores_list:
            return {"error": f"No stores found in {city}"}
        
        return stores_list
    except Exception as e:
        return {"error": f"Failed to get stores: {str(e)}"}
    finally:
        client.close()

# get closest store to customer address
@mcp.tool
def get_closest_store(address: str, city: str) -> dict:
    """
    Main function if customer discloses exact address.
    It retrieves latitude and longitude from it, and then
    computes distance (in km) between each store and the address.
    Returns the store ID and distance of closest store.
    
    :param address: Customer address
    :type address: str
    :param city: City name
    :type city: str
    :return: Dict with store_id and distance_km
    :rtype: dict
    """
    try:
        stores = get_near_stores(city=city)
        
        if isinstance(stores, dict) and "error" in stores:
            return stores
        
        customer_coordinates = get_customer_coordinates(address=address)
        
        if isinstance(customer_coordinates, dict) and "error" in customer_coordinates:
            return customer_coordinates
        
        customer_coords = (customer_coordinates['lat'], customer_coordinates['lng'])
        
        distances = {}
        for doc in stores:
            store_coords = (doc['latitude'], doc['longitude'])
            distance = geopy.distance.geodesic(customer_coords, store_coords).km
            distances[doc['_id']] = distance

        if not distances:
            return {"error": "No stores found to calculate distance"}
        
        min_store_id = min(distances, key=distances.get)
        min_distance = distances[min_store_id]
        
        return {
            "store_id": min_store_id,
            "distance_km": round(min_distance, 2)
        }
    except Exception as e:
        return {"error": f"Failed to find closest store: {str(e)}"}

# get a store information
@mcp.tool
def get_store_info(store_id: str, db: str = "stylistai", collection: str = "stores") -> dict:
    """
    Retrieves the matching document in mongo collection for a given id.
    Store ID is converted to a ObjectID(). In case of error, None is returned.
    
    :param store_id: store_id to look for in collection
    :type store_id: str
    :param db: Mongo DB to use
    :type db: str
    :param collection: Collection to use from Mongo DB
    :type collection: str
    :return: a dictionary with all information on selected store
    :rtype: dict
    """
    try:
        client = MongoClient(config['MONGO_CONNECTION_STRING'])
        db_conn = client[db]
        stores_collection = db_conn[collection]

        try:
            query_id = ObjectId(store_id)
        except Exception as e:
            return {"error": f"Invalid store_id format: {str(e)}"}
        
        doc = stores_collection.find_one({'_id': query_id})
        
        if doc is None:
            return {"error": f"Store with id {store_id} not found"}

        return mongo_to_dict(doc)
    except Exception as e:
        return {"error": f"Failed to get store info: {str(e)}"}
    finally:
        client.close()

# compare a user query with articles embeddings
@mcp.tool()
async def search_catalog(query_text: str, limit: int = 5) -> str:
    """
    Search the H&M fashion catalog for products using semantic similarity.
    Use this tool when the user describes a style, color, or specific clothing item.
    
    Args:
        query_text: The natural language description of the item (e.g., 'blue summer dress').
        limit: Number of items to return (default is 5).
    """
    async with httpx.AsyncClient() as http_client:
        payload = {
            "model": "embeddinggemma",
            "prompt": query_text
        }
        
        try:
            resp = await http_client.post(OLLAMA_URL, json=payload, timeout=60.0)
            resp.raise_for_status()
            vector = resp.json()['embedding']

            async_qdrant = AsyncQdrantClient(url=QDRANT_URL)
            results = await async_qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=vector,
                limit=limit,
                with_payload=True
            )

            if not results.points:
                return "No matching items found in the catalog."

            formatted_results = []
            for hit in results.points:
                p = hit.payload
                item_str = (
                    f"- {p.get('prod_name', 'Unknown Item')} "
                    f"(ID: {p.get('article_id')})\n"
                    f"  Section: {p.get('article_section')}\n"
                    f"  Description: {p.get('description')}\n"
                    f"  Match Score: {hit.score:.2f}"
                )
                formatted_results.append(item_str)

            return "\n\n".join(formatted_results)

        except Exception as e:
            error_msg = f"Error during catalog search: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return error_msg

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001)
