"""
MCP Server for suggestions from Reddit comments and Sports venue finder
Search subreddits, get posts, and read comments. Find sports venues near you.
"""

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Reddit")

# Reddit API base URL (no auth needed for public data)
BASE_URL = "https://www.reddit.com"


@mcp.tool()
async def search_subreddit(subreddit: str, query: str, limit: int = 10) -> dict:
    """Search for posts in a subreddit
    
    Args:
        subreddit: Name of the subreddit (e.g., 'python', 'machinelearning')
        query: Search query
        limit: Number of results to return (default: 10, max: 100)
    """
    url = f"{BASE_URL}/r/{subreddit}/search.json"
    params = {
        "q": query,
        "restrict_sr": "on",  # Restrict search to this subreddit
        "limit": min(limit, 100),
        "sort": "relevance"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title"),
            "author": post.get("author"),
            "score": post.get("score"),
            "num_comments": post.get("num_comments"),
            "created_utc": post.get("created_utc"),
            "url": f"{BASE_URL}{post.get('permalink')}",
            "post_id": post.get("id"),
            "selftext": post.get("selftext", "")[:500]  # First 500 chars
        })
    
    return {
        "subreddit": subreddit,
        "query": query,
        "count": len(posts),
        "posts": posts
    }


@mcp.tool()
async def get_subreddit_hot(subreddit: str, limit: int = 10) -> dict:
    """Get hot posts from a subreddit
    
    Args:
        subreddit: Name of the subreddit (e.g., 'python', 'news')
        limit: Number of posts to return (default: 10, max: 100)
    """
    url = f"{BASE_URL}/r/{subreddit}/hot.json"
    params = {"limit": min(limit, 100)}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title"),
            "author": post.get("author"),
            "score": post.get("score"),
            "num_comments": post.get("num_comments"),
            "created_utc": post.get("created_utc"),
            "url": f"{BASE_URL}{post.get('permalink')}",
            "post_id": post.get("id"),
            "selftext": post.get("selftext", "")[:500]
        })
    
    return {
        "subreddit": subreddit,
        "type": "hot",
        "count": len(posts),
        "posts": posts
    }


@mcp.tool()
async def get_subreddit_new(subreddit: str, limit: int = 10) -> dict:
    """Get newest posts from a subreddit
    
    Args:
        subreddit: Name of the subreddit
        limit: Number of posts to return (default: 10, max: 100)
    """
    url = f"{BASE_URL}/r/{subreddit}/new.json"
    params = {"limit": min(limit, 100)}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title"),
            "author": post.get("author"),
            "score": post.get("score"),
            "num_comments": post.get("num_comments"),
            "created_utc": post.get("created_utc"),
            "url": f"{BASE_URL}{post.get('permalink')}",
            "post_id": post.get("id"),
            "selftext": post.get("selftext", "")[:500]
        })
    
    return {
        "subreddit": subreddit,
        "type": "new",
        "count": len(posts),
        "posts": posts
    }


@mcp.tool()
async def get_subreddit_top(subreddit: str, time_filter: str = "day", limit: int = 10) -> dict:
    """Get top posts from a subreddit
    
    Args:
        subreddit: Name of the subreddit
        time_filter: Time period - 'hour', 'day', 'week', 'month', 'year', 'all' (default: 'day')
        limit: Number of posts to return (default: 10, max: 100)
    """
    url = f"{BASE_URL}/r/{subreddit}/top.json"
    params = {
        "t": time_filter,
        "limit": min(limit, 100)
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title"),
            "author": post.get("author"),
            "score": post.get("score"),
            "num_comments": post.get("num_comments"),
            "created_utc": post.get("created_utc"),
            "url": f"{BASE_URL}{post.get('permalink')}",
            "post_id": post.get("id"),
            "selftext": post.get("selftext", "")[:500]
        })
    
    return {
        "subreddit": subreddit,
        "type": "top",
        "time_filter": time_filter,
        "count": len(posts),
        "posts": posts
    }


@mcp.tool()
async def get_post_content(subreddit: str, post_id: str) -> dict:
    """Get full content of a specific post
    
    Args:
        subreddit: Name of the subreddit
        post_id: The post ID (from search results)
    """
    url = f"{BASE_URL}/r/{subreddit}/comments/{post_id}.json"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    
    # First element is the post
    post_data = data[0].get("data", {}).get("children", [])[0].get("data", {})
    
    return {
        "post_id": post_id,
        "title": post_data.get("title"),
        "author": post_data.get("author"),
        "score": post_data.get("score"),
        "upvote_ratio": post_data.get("upvote_ratio"),
        "num_comments": post_data.get("num_comments"),
        "created_utc": post_data.get("created_utc"),
        "selftext": post_data.get("selftext", ""),
        "url": post_data.get("url"),
        "permalink": f"{BASE_URL}{post_data.get('permalink')}",
        "is_video": post_data.get("is_video", False),
        "link_flair_text": post_data.get("link_flair_text", "")
    }


@mcp.tool()
async def get_post_comments(subreddit: str, post_id: str, limit: int = 20) -> dict:
    """Get comments from a post
    
    Args:
        subreddit: Name of the subreddit
        post_id: The post ID
        limit: Number of top-level comments to return (default: 20)
    """
    url = f"{BASE_URL}/r/{subreddit}/comments/{post_id}.json"
    params = {"limit": limit}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    # Second element contains comments
    comments_data = data[1].get("data", {}).get("children", [])
    
    comments = []
    for child in comments_data:
        comment = child.get("data", {})
        
        # Skip "more comments" entries
        if child.get("kind") != "t1":
            continue
        
        comments.append({
            "author": comment.get("author"),
            "body": comment.get("body", ""),
            "score": comment.get("score"),
            "created_utc": comment.get("created_utc"),
            "edited": comment.get("edited", False),
            "is_submitter": comment.get("is_submitter", False),
            "permalink": f"{BASE_URL}{comment.get('permalink')}"
        })
    
    return {
        "post_id": post_id,
        "subreddit": subreddit,
        "comment_count": len(comments),
        "comments": comments
    }


@mcp.tool()
async def get_user_posts(username: str, limit: int = 10) -> dict:
    """Get recent posts from a user
    
    Args:
        username: Reddit username (without u/)
        limit: Number of posts to return (default: 10, max: 100)
    """
    url = f"{BASE_URL}/user/{username}/submitted.json"
    params = {"limit": min(limit, 100)}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title"),
            "subreddit": post.get("subreddit"),
            "score": post.get("score"),
            "num_comments": post.get("num_comments"),
            "created_utc": post.get("created_utc"),
            "url": f"{BASE_URL}{post.get('permalink')}",
            "post_id": post.get("id")
        })
    
    return {
        "username": username,
        "count": len(posts),
        "posts": posts
    }


@mcp.tool()
async def get_user_comments(username: str, limit: int = 10) -> dict:
    """Get recent comments from a user
    
    Args:
        username: Reddit username (without u/)
        limit: Number of comments to return (default: 10, max: 100)
    """
    url = f"{BASE_URL}/user/{username}/comments.json"
    params = {"limit": min(limit, 100)}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    comments = []
    for child in data.get("data", {}).get("children", []):
        comment = child.get("data", {})
        comments.append({
            "body": comment.get("body", ""),
            "subreddit": comment.get("subreddit"),
            "score": comment.get("score"),
            "created_utc": comment.get("created_utc"),
            "permalink": f"{BASE_URL}{comment.get('permalink')}"
        })
    
    return {
        "username": username,
        "count": len(comments),
        "comments": comments
    }


if __name__ == "__main__":
    mcp.run()