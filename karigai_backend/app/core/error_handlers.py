"""
Comprehensive error handling middleware and utilities.
Provides consistent error responses and user-friendly feedback.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union, Dict, Any

logger = logging.getLogger(__name__)


class KarigAIException(Exception):
    """Base exception for KarigAI application"""
    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class VoiceProcessingError(KarigAIException):
    """Exception for voice processing errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=422, details=details)


class VisionProcessingError(KarigAIException):
    """Exception for vision processing errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=422, details=details)


class DocumentGenerationError(KarigAIException):
    """Exception for document generation errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=500, details=details)


class ServiceUnavailableError(KarigAIException):
    """Exception for service unavailability"""
    def __init__(self, service_name: str, details: Dict[str, Any] = None):
        message = f"Service {service_name} is currently unavailable"
        super().__init__(message, status_code=503, details=details)


async def karigai_exception_handler(request: Request, exc: KarigAIException):
    """Handle KarigAI custom exceptions"""
    logger.error(f"KarigAI Exception: {exc.message}", extra={
        "status_code": exc.status_code,
        "details": exc.details,
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "user_message": get_user_friendly_message(exc)
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP Exception: {exc.detail}", extra={
        "status_code": exc.status_code,
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": request.url.path,
            "user_message": get_http_user_message(exc.status_code)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation Error: {exc.errors()}", extra={
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "path": request.url.path,
            "user_message": "कृपया अपनी जानकारी जांचें और फिर से प्रयास करें। (Please check your information and try again.)"
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected Exception: {str(exc)}", exc_info=True, extra={
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "path": request.url.path,
            "user_message": "कुछ गलत हो गया। कृपया बाद में पुनः प्रयास करें। (Something went wrong. Please try again later.)"
        }
    )


def get_user_friendly_message(exc: KarigAIException) -> str:
    """Get user-friendly error message in Hindi/English"""
    error_messages = {
        VoiceProcessingError: "आवाज़ को समझने में समस्या हुई। कृपया फिर से बोलें। (Problem understanding voice. Please speak again.)",
        VisionProcessingError: "तस्वीर को समझने में समस्या हुई। कृपया फिर से फोटो लें। (Problem understanding image. Please take photo again.)",
        DocumentGenerationError: "दस्तावेज़ बनाने में समस्या हुई। कृपया फिर से प्रयास करें। (Problem creating document. Please try again.)",
        ServiceUnavailableError: "सेवा अभी उपलब्ध नहीं है। कृपया बाद में प्रयास करें। (Service not available now. Please try later.)"
    }
    
    return error_messages.get(type(exc), exc.message)


def get_http_user_message(status_code: int) -> str:
    """Get user-friendly message for HTTP status codes"""
    messages = {
        400: "गलत जानकारी। कृपया जांचें। (Invalid information. Please check.)",
        401: "कृपया लॉगिन करें। (Please login.)",
        403: "आपको इसकी अनुमति नहीं है। (You don't have permission.)",
        404: "नहीं मिला। (Not found.)",
        429: "बहुत सारे अनुरोध। कृपया प्रतीक्षा करें। (Too many requests. Please wait.)",
        500: "सर्वर में समस्या। कृपया बाद में प्रयास करें। (Server problem. Please try later.)",
        503: "सेवा उपलब्ध नहीं है। (Service unavailable.)"
    }
    
    return messages.get(status_code, "कुछ गलत हो गया। (Something went wrong.)")


def register_error_handlers(app):
    """Register all error handlers with FastAPI app"""
    app.add_exception_handler(KarigAIException, karigai_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
