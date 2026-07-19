"""JobScrapper application package.

The HTTP framework is imported lazily so persistence/domain modules remain
usable by workers, migrations, and tests without installing FastAPI.
"""

def create_app(*args, **kwargs):
    from .factory import create_app as factory
    return factory(*args, **kwargs)

__all__ = ["create_app"]
