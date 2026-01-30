from fastmcp import FastMCP
import requests

RECOMMENDER_URL = "http://stylistai-api:8000/invoke"

mcp = FastMCP("StylistAI")

@mcp.tool
def recommender_tool(customer_id: str, top_k: int = 5,
                    exclude_purchased: bool = True,
                    url : str = "http://stylistai-api:8000/invoke"):
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
    """

    payload = {
        "customer_id": customer_id,
        "top_k": top_k,
        "exclude_purchased": exclude_purchased,
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()[0]


if __name__ == "__main__":
    mcp.run()
