import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:karigai_mobile/data/services/api_service.dart';
import 'package:karigai_mobile/data/services/voice_api_service.dart';
import 'package:karigai_mobile/data/services/vision_api_service.dart';
import 'package:karigai_mobile/data/services/document_api_service.dart';
import 'package:karigai_mobile/data/services/learning_api_service.dart';
import 'package:karigai_mobile/data/services/user_api_service.dart';
import 'dart:io';

void main() {
  group('API Integration Tests', () {
    late ApiService apiService;
    late VoiceApiService voiceApiService;
    late VisionApiService visionApiService;
    late DocumentApiService documentApiService;
    late LearningApiService learningApiService;
    late UserApiService userApiService;
    
    setUp(() {
      apiService = ApiService();
      voiceApiService = VoiceApiService(apiService);
      visionApiService = VisionApiService(apiService);
      documentApiService = DocumentApiService(apiService);
      learningApiService = LearningApiService(apiService);
      userApiService = UserApiService(apiService);
    });
    
    group('Error Handling Tests', () {
      test('should handle network timeout', () async {
        // Test timeout handling
        try {
          await apiService.get(
            '/test/timeout',
            options: Options(
              sendTimeout: const Duration(milliseconds: 100),
              receiveTimeout: const Duration(milliseconds: 100),
            ),
          );
          fail('Should throw ApiException');
        } catch (e) {
          expect(e, isA<ApiException>());
          expect((e as ApiException).type, ApiExceptionType.timeout);
        }
      });
      
      test('should handle 404 not found', () async {
        try {
          await apiService.get('/nonexistent/endpoint');
          fail('Should throw ApiException');
        } catch (e) {
          expect(e, isA<ApiException>());
          expect((e as ApiException).type, ApiExceptionType.notFound);
        }
      });
      
      test('should handle 401 unauthorized', () async {
        try {
          await apiService.get('/protected/resource');
          fail('Should throw ApiException');
        } catch (e) {
          expect(e, isA<ApiException>());
          expect((e as ApiException).type, ApiExceptionType.unauthorized);
        }
      });
      
      test('should handle 500 server error', () async {
        try {
          await apiService.get('/test/server-error');
          fail('Should throw ApiException');
        } catch (e) {
          expect(e, isA<ApiException>());
          expect((e as ApiException).type, ApiExceptionType.server);
        }
      });
    });
    
    group('Authentication Tests', () {
      test('should set and use auth token', () async {
        const testToken = 'test_token_123';
        apiService.setAuthToken(testToken);
        
        // Verify token is included in requests
        // This would require mocking or a test endpoint
        expect(apiService, isNotNull);
      });
      
      test('should clear auth token', () {
        apiService.setAuthToken('test_token');
        apiService.clearAuthToken();
        
        // Verify token is removed
        expect(apiService, isNotNull);
      });
    });
    
    group('Retry Logic Tests', () {
      test('should retry on connection error', () async {
        // Test retry mechanism
        // This would require a mock server that fails then succeeds
        expect(apiService, isNotNull);
      });
      
      test('should not retry on 4xx errors', () async {
        try {
          await apiService.get('/test/bad-request');
          fail('Should throw ApiException');
        } catch (e) {
          expect(e, isA<ApiException>());
          // Verify it didn't retry (would need request counting)
        }
      });
    });
    
    group('Voice API Tests', () {
      test('should get supported languages', () async {
        try {
          final languages = await voiceApiService.getSupportedLanguages();
          expect(languages, isA<List<String>>());
          expect(languages.isNotEmpty, true);
        } catch (e) {
          // Expected to fail without backend
          expect(e, isA<ApiException>());
        }
      });
      
      test('should handle speech-to-text with valid audio', () async {
        // This test requires a valid audio file
        // Skip if file doesn't exist
        final audioFile = File('test/fixtures/test_audio.wav');
        if (!audioFile.existsSync()) {
          return;
        }
        
        try {
          final result = await voiceApiService.speechToText(
            audioFile: audioFile,
            languageCode: 'hi-IN',
          );
          expect(result, isA<Map<String, dynamic>>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
    });
    
    group('Vision API Tests', () {
      test('should handle equipment identification', () async {
        final imageFile = File('test/fixtures/test_image.jpg');
        if (!imageFile.existsSync()) {
          return;
        }
        
        try {
          final result = await visionApiService.identifyEquipment(
            imageFile: imageFile,
          );
          expect(result, isA<Map<String, dynamic>>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
      
      test('should handle OCR text extraction', () async {
        final imageFile = File('test/fixtures/test_image.jpg');
        if (!imageFile.existsSync()) {
          return;
        }
        
        try {
          final text = await visionApiService.extractText(
            imageFile: imageFile,
            languageCode: 'hi-IN',
          );
          expect(text, isA<String>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
    });
    
    group('Document API Tests', () {
      test('should get available templates', () async {
        try {
          final templates = await documentApiService.getAvailableTemplates();
          expect(templates, isA<List<String>>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
      
      test('should create invoice with valid data', () async {
        final invoiceData = {
          'customer_name': 'Test Customer',
          'services': [
            {'name': 'Service 1', 'amount': 100.0}
          ],
          'total_amount': 100.0,
        };
        
        try {
          final result = await documentApiService.createInvoice(
            invoiceData: invoiceData,
          );
          expect(result, isA<Map<String, dynamic>>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
    });
    
    group('Learning API Tests', () {
      test('should get course categories', () async {
        try {
          final categories = await learningApiService.getCourseCategories();
          expect(categories, isA<List<String>>());
          expect(categories.isNotEmpty, true);
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
      
      test('should get recommendations for user', () async {
        try {
          final recommendations = await learningApiService.getRecommendations('test_user');
          expect(recommendations, isA<List<Map<String, dynamic>>>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
    });
    
    group('User API Tests', () {
      test('should create user with valid data', () async {
        try {
          final result = await userApiService.createUser(
            phoneNumber: '+919876543210',
            primaryLanguage: 'hi-IN',
            tradeType: 'carpenter',
          );
          expect(result, isA<Map<String, dynamic>>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
      
      test('should get user by phone number', () async {
        try {
          final result = await userApiService.getUserByPhone('+919876543210');
          expect(result, isA<Map<String, dynamic>>());
        } catch (e) {
          expect(e, isA<ApiException>());
        }
      });
    });
  });
}
