"""
Multilingual Content Generation Service

This service generates professional content in multiple languages for
hospitality and tourism use cases, with culturally appropriate responses.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ContentType(Enum):
    """Types of content that can be generated"""
    GUEST_INFORMATION = "guest_information"
    BOOKING_CONFIRMATION = "booking_confirmation"
    WELCOME_MESSAGE = "welcome_message"
    PROMOTIONAL_CONTENT = "promotional_content"
    FACILITY_DESCRIPTION = "facility_description"
    LOCAL_GUIDE = "local_guide"


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    FRENCH = "fr"
    HINDI = "hi"


@dataclass
class ContentRequest:
    """Request for content generation"""
    content_type: ContentType
    languages: List[Language]
    context: Dict[str, any]
    cultural_preferences: Optional[Dict[str, str]] = None


@dataclass
class GeneratedContent:
    """Generated content in multiple languages"""
    content_type: ContentType
    content_by_language: Dict[Language, str]
    metadata: Dict[str, any]


class MultilingualContentService:
    """
    Service for generating multilingual content for hospitality
    
    Provides:
    - Professional content generation in English, French, Hindi
    - Culturally appropriate responses
    - Context-aware content customization
    - Booking communication templates
    """
    
    def __init__(self):
        """Initialize multilingual content service"""
        self.content_templates = self._initialize_templates()
        self.cultural_guidelines = self._initialize_cultural_guidelines()
    
    def generate_content(self, request: ContentRequest) -> GeneratedContent:
        """
        Generate content in multiple languages
        
        Args:
            request: ContentRequest with type, languages, and context
            
        Returns:
            GeneratedContent with content in all requested languages
        """
        content_by_language = {}
        
        for language in request.languages:
            content = self._generate_for_language(
                request.content_type,
                language,
                request.context,
                request.cultural_preferences
            )
            content_by_language[language] = content
        
        return GeneratedContent(
            content_type=request.content_type,
            content_by_language=content_by_language,
            metadata={
                "languages": [lang.value for lang in request.languages],
                "context_keys": list(request.context.keys())
            }
        )
    
    def generate_guest_information(
        self,
        guest_name: str,
        property_name: str,
        check_in_date: str,
        check_out_date: str,
        languages: List[Language]
    ) -> GeneratedContent:
        """
        Generate guest information in multiple languages
        
        Args:
            guest_name: Name of the guest
            property_name: Name of the property
            check_in_date: Check-in date
            check_out_date: Check-out date
            languages: List of languages to generate content in
            
        Returns:
            GeneratedContent with guest information
        """
        context = {
            "guest_name": guest_name,
            "property_name": property_name,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date
        }
        
        request = ContentRequest(
            content_type=ContentType.GUEST_INFORMATION,
            languages=languages,
            context=context
        )
        
        return self.generate_content(request)
    
    def generate_booking_confirmation(
        self,
        booking_id: str,
        guest_name: str,
        property_name: str,
        room_type: str,
        check_in_date: str,
        check_out_date: str,
        total_amount: float,
        languages: List[Language]
    ) -> GeneratedContent:
        """
        Generate booking confirmation in multiple languages
        
        Args:
            booking_id: Booking identifier
            guest_name: Name of the guest
            property_name: Name of the property
            room_type: Type of room booked
            check_in_date: Check-in date
            check_out_date: Check-out date
            total_amount: Total booking amount
            languages: List of languages to generate content in
            
        Returns:
            GeneratedContent with booking confirmation
        """
        context = {
            "booking_id": booking_id,
            "guest_name": guest_name,
            "property_name": property_name,
            "room_type": room_type,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "total_amount": total_amount
        }
        
        request = ContentRequest(
            content_type=ContentType.BOOKING_CONFIRMATION,
            languages=languages,
            context=context
        )
        
        return self.generate_content(request)
    
    def generate_welcome_message(
        self,
        guest_name: str,
        property_name: str,
        host_name: str,
        languages: List[Language],
        cultural_preferences: Optional[Dict[str, str]] = None
    ) -> GeneratedContent:
        """
        Generate welcome message in multiple languages
        
        Args:
            guest_name: Name of the guest
            property_name: Name of the property
            host_name: Name of the host
            languages: List of languages to generate content in
            cultural_preferences: Optional cultural customization
            
        Returns:
            GeneratedContent with welcome message
        """
        context = {
            "guest_name": guest_name,
            "property_name": property_name,
            "host_name": host_name
        }
        
        request = ContentRequest(
            content_type=ContentType.WELCOME_MESSAGE,
            languages=languages,
            context=context,
            cultural_preferences=cultural_preferences
        )
        
        return self.generate_content(request)
    
    def _generate_for_language(
        self,
        content_type: ContentType,
        language: Language,
        context: Dict[str, any],
        cultural_preferences: Optional[Dict[str, str]]
    ) -> str:
        """
        Generate content for a specific language
        
        Args:
            content_type: Type of content to generate
            language: Target language
            context: Context data for content generation
            cultural_preferences: Optional cultural customization
            
        Returns:
            Generated content string
        """
        template = self.content_templates.get(content_type, {}).get(language, "")
        
        if not template:
            return f"Content not available in {language.value}"
        
        # Apply cultural guidelines
        if cultural_preferences:
            template = self._apply_cultural_customization(
                template,
                language,
                cultural_preferences
            )
        
        # Fill template with context data
        try:
            content = template.format(**context)
        except KeyError as e:
            content = f"Error generating content: missing context key {e}"
        
        return content
    
    def _apply_cultural_customization(
        self,
        template: str,
        language: Language,
        preferences: Dict[str, str]
    ) -> str:
        """
        Apply cultural customization to template
        
        Args:
            template: Content template
            language: Target language
            preferences: Cultural preferences
            
        Returns:
            Customized template
        """
        guidelines = self.cultural_guidelines.get(language, {})
        
        # Apply formality level
        if "formality" in preferences:
            formality = preferences["formality"]
            if formality == "formal" and language == Language.FRENCH:
                template = template.replace("tu", "vous")
            elif formality == "informal" and language == Language.HINDI:
                template = template.replace("आप", "तुम")
        
        return template
    
    def _initialize_templates(self) -> Dict[ContentType, Dict[Language, str]]:
        """Initialize content templates for all types and languages"""
        return {
            ContentType.GUEST_INFORMATION: {
                Language.ENGLISH: (
                    "Dear {guest_name},\n\n"
                    "Welcome to {property_name}!\n\n"
                    "Your reservation details:\n"
                    "Check-in: {check_in_date}\n"
                    "Check-out: {check_out_date}\n\n"
                    "We look forward to hosting you.\n\n"
                    "Best regards,\n"
                    "{property_name} Team"
                ),
                Language.FRENCH: (
                    "Cher/Chère {guest_name},\n\n"
                    "Bienvenue à {property_name}!\n\n"
                    "Détails de votre réservation:\n"
                    "Arrivée: {check_in_date}\n"
                    "Départ: {check_out_date}\n\n"
                    "Nous avons hâte de vous accueillir.\n\n"
                    "Cordialement,\n"
                    "L'équipe de {property_name}"
                ),
                Language.HINDI: (
                    "प्रिय {guest_name},\n\n"
                    "{property_name} में आपका स्वागत है!\n\n"
                    "आपके आरक्षण का विवरण:\n"
                    "चेक-इन: {check_in_date}\n"
                    "चेक-आउट: {check_out_date}\n\n"
                    "हम आपकी मेजबानी करने के लिए उत्सुक हैं।\n\n"
                    "सादर,\n"
                    "{property_name} टीम"
                )
            },
            ContentType.BOOKING_CONFIRMATION: {
                Language.ENGLISH: (
                    "Booking Confirmation\n\n"
                    "Booking ID: {booking_id}\n"
                    "Guest Name: {guest_name}\n"
                    "Property: {property_name}\n"
                    "Room Type: {room_type}\n"
                    "Check-in: {check_in_date}\n"
                    "Check-out: {check_out_date}\n"
                    "Total Amount: ₹{total_amount}\n\n"
                    "Your booking has been confirmed. We look forward to welcoming you!"
                ),
                Language.FRENCH: (
                    "Confirmation de Réservation\n\n"
                    "ID de réservation: {booking_id}\n"
                    "Nom du client: {guest_name}\n"
                    "Propriété: {property_name}\n"
                    "Type de chambre: {room_type}\n"
                    "Arrivée: {check_in_date}\n"
                    "Départ: {check_out_date}\n"
                    "Montant total: ₹{total_amount}\n\n"
                    "Votre réservation a été confirmée. Nous avons hâte de vous accueillir!"
                ),
                Language.HINDI: (
                    "बुकिंग पुष्टिकरण\n\n"
                    "बुकिंग आईडी: {booking_id}\n"
                    "अतिथि का नाम: {guest_name}\n"
                    "संपत्ति: {property_name}\n"
                    "कमरे का प्रकार: {room_type}\n"
                    "चेक-इन: {check_in_date}\n"
                    "चेक-आउट: {check_out_date}\n"
                    "कुल राशि: ₹{total_amount}\n\n"
                    "आपकी बुकिंग की पुष्टि हो गई है। हम आपका स्वागत करने के लिए उत्सुक हैं!"
                )
            },
            ContentType.WELCOME_MESSAGE: {
                Language.ENGLISH: (
                    "Dear {guest_name},\n\n"
                    "Welcome to {property_name}!\n\n"
                    "I'm {host_name}, your host. Please feel free to reach out "
                    "if you need anything during your stay. We want to make your "
                    "experience memorable.\n\n"
                    "Warm regards,\n"
                    "{host_name}"
                ),
                Language.FRENCH: (
                    "Cher/Chère {guest_name},\n\n"
                    "Bienvenue à {property_name}!\n\n"
                    "Je suis {host_name}, votre hôte. N'hésitez pas à me contacter "
                    "si vous avez besoin de quoi que ce soit pendant votre séjour. "
                    "Nous voulons rendre votre expérience mémorable.\n\n"
                    "Cordialement,\n"
                    "{host_name}"
                ),
                Language.HINDI: (
                    "प्रिय {guest_name},\n\n"
                    "{property_name} में आपका स्वागत है!\n\n"
                    "मैं {host_name}, आपका मेजबान हूं। यदि आपको अपने प्रवास के दौरान "
                    "किसी भी चीज़ की आवश्यकता हो तो कृपया बेझिझक संपर्क करें। हम आपके "
                    "अनुभव को यादगार बनाना चाहते हैं।\n\n"
                    "सादर,\n"
                    "{host_name}"
                )
            }
        }
    
    def _initialize_cultural_guidelines(self) -> Dict[Language, Dict[str, str]]:
        """Initialize cultural guidelines for each language"""
        return {
            Language.ENGLISH: {
                "greeting_style": "professional_friendly",
                "formality": "moderate",
                "tone": "warm_professional"
            },
            Language.FRENCH: {
                "greeting_style": "formal_polite",
                "formality": "high",
                "tone": "respectful_elegant"
            },
            Language.HINDI: {
                "greeting_style": "respectful_warm",
                "formality": "moderate_high",
                "tone": "hospitable_respectful"
            }
        }
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return [lang.value for lang in Language]
    
    def get_supported_content_types(self) -> List[str]:
        """Get list of supported content types"""
        return [ct.value for ct in ContentType]
