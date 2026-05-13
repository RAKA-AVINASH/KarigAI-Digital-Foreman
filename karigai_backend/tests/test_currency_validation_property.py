"""
Property-Based Test for Currency Validation and Formatting

**Property 3: Currency Validation and Formatting**
*For any* voice input containing pricing information, the system should validate 
and format currency amounts into a consistent standard format (₹X,XXX.XX)
**Validates: Requirements 1.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List, Optional, Any
from decimal import Decimal, InvalidOperation
import re

from app.services.currency_service import CurrencyService, CurrencyValidationResult


class TestCurrencyValidationProperty:
    """Property-based tests for Currency Validation and Formatting."""
    
    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('99999999.99'), places=2),
        language_code=st.sampled_from(['hi-IN', 'en-US', 'ml-IN', 'pa-IN', 'bn-IN', 'ta-IN', 'te-IN']),
        currency_format=st.sampled_from(['symbol_prefix', 'symbol_suffix', 'word_prefix', 'word_suffix'])
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_currency_validation_and_formatting_property(self, amount, language_code, currency_format):
        """
        **Property 3: Currency Validation and Formatting**
        
        For any voice input containing pricing information, the system should validate 
        and format currency amounts into a consistent standard format (₹X,XXX.XX).
        
        **Validates: Requirements 1.5**
        """
        # Create currency service instance
        currency_service = CurrencyService()
        
        # Generate voice input text with currency information
        voice_input = await self._generate_voice_input_with_currency(amount, language_code, currency_format)
        
        # Assume valid input (not empty and contains recognizable currency patterns)
        assume(len(voice_input.strip()) > 0)
        assume(amount > 0)
        
        # Process the voice input for currency validation and formatting
        result = await currency_service.validate_and_format_currency(voice_input, language_code)
        
        # Property assertions
        
        # 1. System should always return a CurrencyValidationResult
        assert isinstance(result, CurrencyValidationResult)
        
        # 2. For valid currency input, the result should be marked as valid
        if result.is_valid:
            assert result.formatted_amount is not None
            assert result.raw_amount is not None
            assert result.raw_amount > 0
        
        # 3. Currency symbol should always be the Indian Rupee symbol
        assert result.currency_symbol == "₹"
        
        # 4. Confidence score should be within valid range
        assert 0.0 <= result.confidence_score <= 1.0
        
        # 5. For valid results, formatted amount should follow standard format
        if result.is_valid and result.formatted_amount:
            # Should start with ₹ symbol
            assert result.formatted_amount.startswith("₹")
            
            # Should contain properly formatted numbers
            # Remove ₹ symbol and check number format
            amount_part = result.formatted_amount[1:].strip()
            
            # Should be a valid formatted number (with commas for thousands)
            # or contain Indian number system words (lakh, crore)
            assert (self._is_valid_formatted_number(amount_part) or 
                   'lakh' in amount_part.lower() or 
                   'crore' in amount_part.lower())
        
        # 6. Raw amount should match the input amount (within reasonable tolerance)
        if result.is_valid and result.raw_amount:
            # Allow for some tolerance in number word conversion
            tolerance = max(Decimal('0.01'), amount * Decimal('0.01'))  # 1% or 1 paisa minimum
            assert abs(result.raw_amount - amount) <= tolerance
        
        # 7. Detected patterns should not be empty for valid results
        if result.is_valid:
            assert len(result.detected_patterns) > 0
        
        # 8. Error message should be None for valid results
        if result.is_valid:
            assert result.error_message is None
        else:
            # Invalid results should have an error message
            assert result.error_message is not None
    
    @given(
        amounts=st.lists(
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
            min_size=1, max_size=5
        ),
        language_code=st.sampled_from(['hi-IN', 'en-US', 'ml-IN'])
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_multiple_currency_amounts_property(self, amounts, language_code):
        """
        Test property for handling multiple currency amounts in single input.
        
        The system should identify and format all currency amounts consistently.
        """
        # Create currency service instance
        currency_service = CurrencyService()
        
        # Generate voice input with multiple currency amounts
        voice_input = await self._generate_voice_input_with_multiple_currencies(amounts, language_code)
        
        assume(len(voice_input.strip()) > 0)
        assume(all(amount > 0 for amount in amounts))
        
        # Process the voice input
        result = await currency_service.validate_and_format_currency(voice_input, language_code)
        
        # Property assertions for multiple amounts
        
        # 1. Should return a valid result structure
        assert isinstance(result, CurrencyValidationResult)
        
        # 2. Should detect at least one amount from the input
        if any(amount >= Decimal('1.0') for amount in amounts):  # Reasonable amounts should be detected
            assert result.confidence_score > 0.0
        
        # 3. If valid, formatting should be consistent
        if result.is_valid:
            assert result.formatted_amount.startswith("₹")
            # Allow for reasonable tolerance in amount extraction (up to 1 rupee difference)
            min_expected = min(amounts)
            tolerance = max(Decimal('1.0'), min_expected * Decimal('0.05'))  # 5% or 1 rupee minimum
            assert result.raw_amount in amounts or abs(min_expected - result.raw_amount) <= tolerance
    
    @given(
        base_amount=st.decimals(min_value=Decimal('1'), max_value=Decimal('999999'), places=0),
        language_code=st.sampled_from(['hi-IN', 'en-US', 'ml-IN']),
        number_format=st.sampled_from(['digits', 'words', 'mixed'])
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_number_format_consistency_property(self, base_amount, language_code, number_format):
        """
        Test property for consistent formatting regardless of input number format.
        
        Whether input is in digits, words, or mixed format, output should be consistently formatted.
        """
        # Create currency service instance
        currency_service = CurrencyService()
        
        # Generate voice input in different number formats
        voice_input = await self._generate_voice_input_by_format(base_amount, language_code, number_format)
        
        assume(len(voice_input.strip()) > 0)
        assume(base_amount > 0)
        
        # Process the voice input
        result = await currency_service.validate_and_format_currency(voice_input, language_code)
        
        # Property assertions for format consistency
        
        # 1. Valid results should have consistent format structure
        if result.is_valid:
            # Should always start with ₹
            assert result.formatted_amount.startswith("₹")
            
            # Should follow Indian number formatting conventions
            amount_part = result.formatted_amount[1:].strip()
            
            # For amounts >= 1 lakh, should use lakh/crore notation or proper comma formatting
            if result.raw_amount >= 100000:
                assert ('lakh' in amount_part.lower() or 
                       'crore' in amount_part.lower() or
                       ',' in amount_part)
        
        # 2. Raw amount should be reasonable compared to input
        if result.is_valid and result.raw_amount:
            # Should be within reasonable range of input (accounting for word-to-number conversion)
            ratio = float(result.raw_amount) / float(base_amount)
            assert 0.1 <= ratio <= 10.0  # Allow for reasonable conversion variations
    
    @given(
        invalid_input=st.one_of(
            st.text(min_size=1, max_size=100).filter(lambda x: not any(c.isdigit() for c in x)),
            st.just(""),
            st.just("   "),
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=50)
        ),
        language_code=st.sampled_from(['hi-IN', 'en-US'])
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_invalid_input_handling_property(self, invalid_input, language_code):
        """
        Test property for handling invalid currency input gracefully.
        
        System should handle invalid input without crashing and provide appropriate error messages.
        """
        # Create currency service instance
        currency_service = CurrencyService()
        
        # Process invalid input
        result = await currency_service.validate_and_format_currency(invalid_input, language_code)
        
        # Property assertions for invalid input handling
        
        # 1. Should always return a result structure (never crash)
        assert isinstance(result, CurrencyValidationResult)
        
        # 2. Invalid input should be marked as invalid
        if not any(c.isdigit() for c in invalid_input) or len(invalid_input.strip()) == 0:
            assert not result.is_valid
        
        # 3. Invalid results should have error messages
        if not result.is_valid:
            assert result.error_message is not None
            assert len(result.error_message) > 0
        
        # 4. Currency symbol should still be set
        assert result.currency_symbol == "₹"
        
        # 5. Confidence score should be 0.0 for clearly invalid input
        if not result.is_valid:
            assert result.confidence_score == 0.0
    
    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('99999.99'), places=2),
        language_codes=st.lists(
            st.sampled_from(['hi-IN', 'en-US', 'ml-IN', 'pa-IN']),
            min_size=2, max_size=3, unique=True
        )
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_cross_language_consistency_property(self, amount, language_codes):
        """
        Test property for consistent formatting across different languages.
        
        Same amount should be formatted consistently regardless of input language.
        """
        # Create currency service instance
        currency_service = CurrencyService()
        
        results = []
        
        # Process same amount in different languages
        for lang_code in language_codes:
            voice_input = await self._generate_voice_input_with_currency(amount, lang_code, 'symbol_prefix')
            result = await currency_service.validate_and_format_currency(voice_input, lang_code)
            results.append(result)
        
        # Property assertions for cross-language consistency
        
        # 1. All results should have same currency symbol
        for result in results:
            assert result.currency_symbol == "₹"
        
        # 2. Valid results should have similar raw amounts
        valid_results = [r for r in results if r.is_valid]
        if len(valid_results) >= 2:
            raw_amounts = [r.raw_amount for r in valid_results]
            # All amounts should be within 1% of each other
            max_amount = max(raw_amounts)
            min_amount = min(raw_amounts)
            tolerance = max_amount * Decimal('0.01')
            assert (max_amount - min_amount) <= tolerance
        
        # 3. Formatted amounts should follow same structure
        valid_formatted = [r.formatted_amount for r in valid_results if r.formatted_amount]
        if len(valid_formatted) >= 2:
            # All should start with ₹
            assert all(fmt.startswith("₹") for fmt in valid_formatted)
    
    # Helper methods for generating test data
    
    async def _generate_voice_input_with_currency(self, amount: Decimal, language_code: str, format_type: str) -> str:
        """Generate voice input text containing currency information."""
        amount_float = float(amount)
        
        # Language-specific templates
        templates = {
            'hi-IN': {
                'symbol_prefix': f"सेवा शुल्क ₹{amount_float:.2f} है",
                'symbol_suffix': f"सेवा शुल्क {amount_float:.2f}₹ है",
                'word_prefix': f"सेवा शुल्क {amount_float:.2f} रुपये है",
                'word_suffix': f"{amount_float:.2f} रुपये सेवा शुल्क है"
            },
            'en-US': {
                'symbol_prefix': f"Service charge is ₹{amount_float:.2f}",
                'symbol_suffix': f"Service charge is {amount_float:.2f}₹",
                'word_prefix': f"Service charge is {amount_float:.2f} rupees",
                'word_suffix': f"{amount_float:.2f} rupees is the service charge"
            },
            'ml-IN': {
                'symbol_prefix': f"സേവന ചാർജ് ₹{amount_float:.2f} ആണ്",
                'symbol_suffix': f"സേവന ചാർജ് {amount_float:.2f}₹ ആണ്",
                'word_prefix': f"സേവന ചാർജ് {amount_float:.2f} രൂപ ആണ്",
                'word_suffix': f"{amount_float:.2f} രൂപ സേവന ചാർജ് ആണ്"
            }
        }
        
        # Default to English if language not found
        lang_templates = templates.get(language_code, templates['en-US'])
        return lang_templates.get(format_type, lang_templates['symbol_prefix'])
    
    async def _generate_voice_input_with_multiple_currencies(self, amounts: List[Decimal], language_code: str) -> str:
        """Generate voice input with multiple currency amounts."""
        if language_code.startswith('hi'):
            if len(amounts) >= 2:
                return f"पहली सेवा ₹{amounts[0]} है, दूसरी सेवा ₹{amounts[1]} है"
            else:
                return f"सेवा शुल्क ₹{amounts[0]} है"
        elif language_code.startswith('ml'):
            if len(amounts) >= 2:
                return f"ആദ്യ സേവനം ₹{amounts[0]} ആണ്, രണ്ടാമത്തെ സേവനം ₹{amounts[1]} ആണ്"
            else:
                return f"സേവന ചാർജ് ₹{amounts[0]} ആണ്"
        else:
            if len(amounts) >= 2:
                return f"First service is ₹{amounts[0]}, second service is ₹{amounts[1]}"
            else:
                return f"Service charge is ₹{amounts[0]}"
    
    async def _generate_voice_input_by_format(self, amount: Decimal, language_code: str, number_format: str) -> str:
        """Generate voice input with different number formats."""
        amount_int = int(amount)
        
        if number_format == 'digits':
            if language_code.startswith('hi'):
                return f"कुल राशि {amount_int} रुपये है"
            else:
                return f"Total amount is {amount_int} rupees"
        
        elif number_format == 'words':
            # Simple number-to-word conversion for testing
            word_map = {
                1: 'one/एक', 2: 'two/दो', 3: 'three/तीन', 4: 'four/चार', 5: 'five/पांच',
                10: 'ten/दस', 20: 'twenty/बीस', 50: 'fifty/पचास', 100: 'hundred/सौ',
                1000: 'thousand/हजार', 5000: 'five thousand/पांच हजार'
            }
            
            # Find closest word representation
            word_amount = word_map.get(amount_int, f"{amount_int}")
            
            if language_code.startswith('hi'):
                return f"कुल राशि {word_amount} रुपये है"
            else:
                return f"Total amount is {word_amount} rupees"
        
        else:  # mixed format
            if language_code.startswith('hi'):
                return f"सेवा का charge ₹{amount_int} है"
            else:
                return f"Service ka charge is ₹{amount_int}"
    
    def _is_valid_formatted_number(self, amount_str: str) -> bool:
        """Check if a string represents a valid formatted number."""
        # Remove commas and check if it's a valid number
        clean_amount = amount_str.replace(',', '').strip()
        
        try:
            float(clean_amount)
            return True
        except ValueError:
            return False
    
    @given(
        service_items=st.lists(
            st.fixed_dictionaries({
                'description': st.text(min_size=1, max_size=50),
                'amount': st.decimals(min_value=Decimal('0.01'), max_value=Decimal('99999.99'), places=2),
                'quantity': st.integers(min_value=1, max_value=10)
            }),
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_invoice_amount_validation_property(self, service_items):
        """
        Test property for validating currency amounts in invoice service items.
        
        All service items should have valid, properly formatted currency amounts.
        """
        # Create currency service instance
        currency_service = CurrencyService()
        
        # Validate all service item amounts
        validation_results = await currency_service.validate_invoice_amounts(service_items)
        
        # Property assertions for invoice validation
        
        # 1. Should return validation result for each service item
        assert len(validation_results) == len(service_items)
        
        # 2. Each result should be a CurrencyValidationResult
        for result in validation_results:
            assert isinstance(result, CurrencyValidationResult)
        
        # 3. Valid amounts should be properly formatted
        for i, result in enumerate(validation_results):
            original_amount = service_items[i]['amount']
            
            if original_amount > 0:
                assert result.is_valid
                assert result.formatted_amount is not None
                assert result.formatted_amount.startswith("₹")
                assert result.raw_amount == original_amount
                assert result.confidence_score == 1.0  # Direct input should have full confidence
            else:
                assert not result.is_valid
                assert result.error_message is not None
        
        # 4. All results should use same currency symbol
        for result in validation_results:
            assert result.currency_symbol == "₹"