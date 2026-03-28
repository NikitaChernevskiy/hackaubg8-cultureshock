"""GZip compression middleware — critical for emergency bundle size."""

from starlette.middleware.gzip import GZipMiddleware

# Compress responses > 500 bytes.
# The emergency bundle target is < 50KB compressed.
GZIP_MINIMUM_SIZE = 500

__all__ = ["GZipMiddleware", "GZIP_MINIMUM_SIZE"]
