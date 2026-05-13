"""
Currency Validation and Formatting Service

This service handles currency validation and formatting for voice input
containing pricing information, ensuring consistent standard format (₹X,XXX.XX).
"""

import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


@dataclass
class CurrencyValidationResult:
    """Result of currency validation and formatting."""
    is_valid: bool
    formatted_amount: Optional[str]
    raw_amount: Optional[Decimal]
    currency_symbol: str
    detected_patterns: List[str]
    confidence_score: float
    error_message: Optional[str] = None


class CurrencyService:
    """Service for currency validation and formatting."""
    
    # Currency patterns for different languages and formats
    CURRENCY_PATTERNS = {
        # English patterns
        'en_rupees': [
            r'(?:rupees?|rs\.?|inr)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:rupees?|rs\.?|inr)',
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ],
        # Hindi patterns
        'hi_rupees': [
            r'(?:रुपये?|रुपया|रु\.?)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:रुपये?|रुपया|रु\.?)',
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ],
        # Malayalam patterns
        'ml_rupees': [
            r'(?:രൂപ|രൂപയ്)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:രൂപ|രൂപയ്)',
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ],
        # Punjabi patterns
        'pa_rupees': [
            r'(?:ਰੁਪਏ|ਰੁਪਿਆ)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:ਰੁਪਏ|ਰੁਪਿਆ)',
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ],
        # Bengali patterns
        'bn_rupees': [
            r'(?:টাকা|রুপি)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:টাকা|রুপি)',
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ],
        # Tamil patterns
        'ta_rupees': [
            r'(?:ரூபாய்|ரூபா)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:ரூபாய்|ரூபா)',
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ],
        # Telugu patterns
        'te_rupees': [
            r'(?:రూపాయలు|రూపాయి)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:రూపాయలు|రూపాయి)',
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ],
        # Number words in different languages
        'number_words': {
            'en': {
                'hundred': 100, 'thousand': 1000, 'lakh': 100000, 'crore': 10000000,
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
                'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
            },
            'hi': {
                'सौ': 100, 'हजार': 1000, 'लाख': 100000, 'करोड़': 10000000,
                'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पांच': 5, 'पाँच': 5,
                'छह': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10,
                'बीस': 20, 'तीस': 30, 'चालीस': 40, 'पचास': 50,
                'साठ': 60, 'सत्तर': 70, 'अस्सी': 80, 'नब्बे': 90
            },
            'ml': {
                'നൂറ്': 100, 'ആയിരം': 1000, 'ലക്ഷം': 100000, 'കോടി': 10000000,
                'ഒന്ന്': 1, 'രണ്ട്': 2, 'മൂന്ന്': 3, 'നാല്': 4, 'അഞ്ച്': 5,
                'ആറ്': 6, 'ഏഴ്': 7, 'എട്ട്': 8, 'ഒമ്പത്': 9, 'പത്ത്': 10,
                'ഇരുപത്': 20, 'മുപ്പത്': 30, 'നാല്പത്': 40, 'അമ്പത്': 50,
                'അറുപത്': 60, 'എഴുപത്': 70, 'എണ്പത്': 80, 'തൊണ്ണൂറ്': 90
            }
        }
    }
    
    def __init__(self):
        """Initialize the currency service."""
        self.compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for better performance."""
        compiled = {}
        for lang, patterns in self.CURRENCY_PATTERNS.items():
            if lang != 'number_words':
                compiled[lang] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled
    
    async def validate_and_format_currency(self, text: str, language_code: str = "hi-IN") -> CurrencyValidationResult:
        """
        Validate and format currency amounts from voice input text.
        
        Args:
            text: Input text containing pricing information
            language_code: Language code for the input text
            
        Returns:
            CurrencyValidationResult with validation and formatting results
        """
        try:
            # Extract currency amounts from text
            detected_amounts = await self._extract_currency_amounts(text, language_code)
            
            if not detected_amounts:
                return CurrencyValidationResult(
                    is_valid=False,
                    formatted_amount=None,
                    raw_amount=None,
                    currency_symbol="₹",
                    detected_patterns=[],
                    confidence_score=0.0,
                    error_message="No currency amounts detected in text"
                )
            
            # Use the first detected amount (highest confidence)
            amount_data = detected_amounts[0]
            raw_amount = amount_data['amount']
            confidence = amount_data['confidence']
            patterns = amount_data['patterns']
            
            # Validate the amount
            if raw_amount <= 0:
                return CurrencyValidationResult(
                    is_valid=False,
                    formatted_amount=None,
                    raw_amount=raw_amount,
                    currency_symbol="₹",
                    detected_patterns=patterns,
                    confidence_score=confidence,
                    error_message="Invalid amount: must be greater than zero"
                )
            
            # Format the amount in standard format (₹X,XXX.XX)
            formatted_amount = await self._format_currency_amount(raw_amount)
            
            return CurrencyValidationResult(
                is_valid=True,
                formatted_amount=formatted_amount,
                raw_amount=raw_amount,
                currency_symbol="₹",
                detected_patterns=patterns,
                confidence_score=confidence
            )
            
        except Exception as e:
            logger.error(f"Error in currency validation: {str(e)}")
            return CurrencyValidationResult(
                is_valid=False,
                formatted_amount=None,
                raw_amount=None,
                currency_symbol="₹",
                detected_patterns=[],
                confidence_score=0.0,
                error_message=f"Processing error: {str(e)}"
            )
    
    async def _extract_currency_amounts(self, text: str, language_code: str) -> List[Dict]:
        """Extract currency amounts from text using pattern matching."""
        detected_amounts = []
        text_lower = text.lower()
        
        # Determine language patterns to use
        lang_prefix = language_code.split('-')[0] if '-' in language_code else language_code
        pattern_keys = [f"{lang_prefix}_rupees", "en_rupees"]  # Always include English as fallback
        
        # Try pattern matching
        for pattern_key in pattern_keys:
            if pattern_key in self.compiled_patterns:
                for pattern in self.compiled_patterns[pattern_key]:
                    matches = pattern.findall(text_lower)
                    for match in matches:
                        try:
                            # Clean and parse the amount
                            amount_str = match.replace(',', '').strip()
                            amount = Decimal(amount_str)
                            
                            detected_amounts.append({
                                'amount': amount,
                                'confidence': 0.9,  # High confidence for direct pattern match
                                'patterns': [pattern_key],
                                'raw_match': match
                            })
                        except (InvalidOperation, ValueError):
                            continue
        
        # Try number word extraction
        word_amounts = await self._extract_number_words(text_lower, lang_prefix)
        detected_amounts.extend(word_amounts)
        
        # Sort by confidence and amount (prefer higher confidence and reasonable amounts)
        detected_amounts.sort(key=lambda x: (x['confidence'], float(x['amount'])), reverse=True)
        
        return detected_amounts
    
    async def _extract_number_words(self, text: str, language_code: str) -> List[Dict]:
        """Extract currency amounts from number words."""
        detected_amounts = []
        
        # Get number words for the language
        lang_words = self.CURRENCY_PATTERNS['number_words'].get(language_code, {})
        if not lang_words:
            lang_words = self.CURRENCY_PATTERNS['number_words']['en']  # Fallback to English
        
        # Look for number word patterns
        words = text.split()
        for i, word in enumerate(words):
            if word in lang_words:
                # Check if followed by currency indicator
                currency_indicators = ['rupees', 'rupee', 'rs', 'inr', 'रुपये', 'रुपया', 'രൂപ', '₹']
                
                # Look ahead for currency indicators
                for j in range(i + 1, min(i + 3, len(words))):
                    if any(indicator in words[j].lower() for indicator in currency_indicators):
                        amount = Decimal(lang_words[word])
                        detected_amounts.append({
                            'amount': amount,
                            'confidence': 0.7,  # Lower confidence for word-based extraction
                            'patterns': ['number_words'],
                            'raw_match': f"{word} {words[j]}"
                        })
                        break
        
        return detected_amounts
    
    async def _format_currency_amount(self, amount: Decimal) -> str:
        """Format currency amount in standard Indian format (₹X,XXX.XX)."""
        # Convert to float for formatting
        amount_float = float(amount)
        
        # Format with Indian number system (lakhs, crores)
        if amount_float >= 10000000:  # 1 crore
            crores = amount_float / 10000000
            if crores == int(crores):
                return f"₹{int(crores):,},00,00,000"
            else:
                return f"₹{crores:,.2f} crore"
        elif amount_float >= 100000:  # 1 lakh
            lakhs = amount_float / 100000
            if lakhs == int(lakhs):
                return f"₹{int(lakhs):,},00,000"
            else:
                return f"₹{lakhs:,.2f} lakh"
        else:
            # Standard formatting for amounts less than 1 lakh
            if amount_float == int(amount_float):
                return f"₹{int(amount_float):,}"
            else:
                return f"₹{amount_float:,.2f}"
    
    async def extract_pricing_from_voice_input(self, transcribed_text: str, 
                                             language_code: str = "hi-IN") -> Dict[str, any]:
        """
        Extract pricing information from voice input for invoice generation.
        
        Args:
            transcribed_text: Text transcribed from voice input
            language_code: Language code of the input
            
        Returns:
            Dictionary containing extracted pricing information
        """
        result = await self.validate_and_format_currency(transcribed_text, language_code)
        
        return {
            'has_pricing': result.is_valid,
            'formatted_amount': result.formatted_amount,
            'raw_amount': float(result.raw_amount) if result.raw_amount else None,
            'currency_symbol': result.currency_symbol,
            'confidence_score': result.confidence_score,
            'detected_patterns': result.detected_patterns,
            'error_message': result.error_message
        }
    
    async def validate_invoice_amounts(self, service_items: List[Dict]) -> List[CurrencyValidationResult]:
        """
        Validate currency amounts in service items for invoice generation.
        
        Args:
            service_items: List of service items with amounts
            
        Returns:
            List of validation results for each service item
        """
        results = []
        
        for item in service_items:
            amount = item.get('amount', 0)
            try:
                decimal_amount = Decimal(str(amount))
                formatted_amount = await self._format_currency_amount(decimal_amount)
                
                results.append(CurrencyValidationResult(
                    is_valid=decimal_amount > 0,
                    formatted_amount=formatted_amount,
                    raw_amount=decimal_amount,
                    currency_symbol="₹",
                    detected_patterns=['direct_input'],
                    confidence_score=1.0,
                    error_message=None if decimal_amount > 0 else "Amount must be greater than zero"
                ))
            except (InvalidOperation, ValueError) as e:
                results.append(CurrencyValidationResult(
                    is_valid=False,
                    formatted_amount=None,
                    raw_amount=None,
                    currency_symbol="₹",
                    detected_patterns=[],
                    confidence_score=0.0,
                    error_message=f"Invalid amount format: {str(e)}"
                ))
        
        return results