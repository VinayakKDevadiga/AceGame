
# somewhere secure, e.g. game_router.py
GAME_ROUTES = {
    "Sokkatte": {
        "app": "Sokkatte",
        "url": "/Sokkatte/",
        "allowed": True,
    },
    "chess": {
        "app": "chess_app",
        "url": "/game/chess/",
        "allowed": True,
    },
    "demo": {
        "app": "demo_app",
        "url": "/game/demo/",
        "allowed": False,  # example of deactivated game
    }
}
