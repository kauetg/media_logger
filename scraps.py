from duckduckgo_search import DDGS

def get_camera_image_duckduckgo(camera_name):
    query = f"{camera_name} site:bhphotovideo.com OR site:dpreview.com"
    with DDGS() as ddgs:
        for result in ddgs.images(query):
            if "bhphotovideo" in result["image"] or "dpreview" in result["image"]:
                return result["image"]  # link direto da imagem
    return None

