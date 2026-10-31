import socket

def is_connected():
    """Verifica se há conexão com a internet tentando acessar o DNS do Google."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False


def get_camera_image_duckduckgo(camera_name):
    """Tenta buscar imagem da câmera com fallback seguro.

    Import de duckduckgo_search é feito aqui dentro (não no topo do módulo) de
    propósito: essa lib puxa binários nativos (primp, lxml) que podem falhar
    para carregar no .exe empacotado (PyInstaller). Se isso acontecer, só essa
    busca fica indisponível em vez de derrubar o app inteiro na inicialização.
    """
    if not is_connected():
        print("[Info] Sem conexão — pulando busca DuckDuckGo.")
        return None

    try:
        from duckduckgo_search import DDGS
    except Exception as e:
        print(f"[Info] duckduckgo_search indisponível — pulando busca de imagem. ({e})")
        return None

    query = f"{camera_name} site:bhphotovideo.com OR site:dpreview.com"

    try:
        with DDGS() as ddgs:
            for result in ddgs.images(query):
                if "bhphotovideo" in result["image"] or "dpreview" in result["image"]:
                    return result["image"]
    except Exception as e:
        print(f"[Erro DuckDuckGo] {e}")
        return None

    return None