from fastapi.middleware.cors import CORSMiddleware


def addCORS(application):
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # FE dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
