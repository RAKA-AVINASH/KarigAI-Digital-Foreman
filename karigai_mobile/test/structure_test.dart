import 'package:flutter_test/flutter_test.dart';
import 'package:karigai_mobile/core/app_config.dart';
import 'package:karigai_mobile/core/constants/app_constants.dart';
import 'package:karigai_mobile/data/models/models.dart';

void main() {
  group('App Configuration Tests', () {
    test('AppConfig should have valid configuration', () {
      expect(AppConfig.appName, 'KarigAI');
      expect(AppConfig.supportedLocales.length, greaterThan(0));
      expect(AppConfig.voiceProcessingTimeout.inSeconds, 3);
      expect(AppConfig.documentGenerationTimeout.inSeconds, 5);
      expect(AppConfig.imageAnalysisTimeout.inSeconds, 10);
    });

    test('AppConstants should have valid values', () {
      expect(AppConstants.appName, 'KarigAI');
      expect(AppConstants.supportedLanguages.length, greaterThan(0));
      expect(AppConstants.tradeTypes.length, greaterThan(0));
      expect(AppConstants.minTouchTargetSize, 48.0);
    });
  });

  group('Data Model Tests', () {
    test('UserModel should serialize and deserialize correctly', () {
      final now = DateTime.now();
      final user = UserModel(
        userId: 'test-123',
        phoneNumber: '+919876543210',
        primaryLanguage: 'hi',
        tradeType: 'Plumber',
        createdAt: now,
        updatedAt: now,
      );

      final json = user.toJson();
      final deserializedUser = UserModel.fromJson(json);

      expect(deserializedUser.userId, user.userId);
      expect(deserializedUser.phoneNumber, user.phoneNumber);
      expect(deserializedUser.primaryLanguage, user.primaryLanguage);
      expect(deserializedUser.tradeType, user.tradeType);
    });

    test('DocumentModel should handle different document types', () {
      final doc = DocumentModel(
        documentId: 'doc-123',
        userId: 'user-123',
        documentType: DocumentType.invoice,
        filePath: '/path/to/doc.pdf',
        createdAt: DateTime.now(),
      );

      expect(doc.documentType, DocumentType.invoice);
      expect(doc.filePath, '/path/to/doc.pdf');

      final json = doc.toJson();
      final deserializedDoc = DocumentModel.fromJson(json);

      expect(deserializedDoc.documentId, doc.documentId);
      expect(deserializedDoc.documentType, doc.documentType);
    });

    test('LearningProgressModel should calculate completion status', () {
      final notStarted = LearningProgressModel(
        progressId: 'prog-1',
        userId: 'user-1',
        courseId: 'course-1',
        completionPercentage: 0.0,
      );

      final inProgress = LearningProgressModel(
        progressId: 'prog-2',
        userId: 'user-1',
        courseId: 'course-2',
        completionPercentage: 0.5,
      );

      final completed = LearningProgressModel(
        progressId: 'prog-3',
        userId: 'user-1',
        courseId: 'course-3',
        completionPercentage: 1.0,
      );

      expect(notStarted.notStarted, true);
      expect(notStarted.isInProgress, false);
      expect(notStarted.isCompleted, false);

      expect(inProgress.notStarted, false);
      expect(inProgress.isInProgress, true);
      expect(inProgress.isCompleted, false);

      expect(completed.notStarted, false);
      expect(completed.isInProgress, false);
      expect(completed.isCompleted, true);
    });

    test('CourseModel should handle prerequisites', () {
      final course = CourseModel(
        courseId: 'course-1',
        title: 'Advanced Plumbing',
        description: 'Learn advanced techniques',
        durationSeconds: 30,
        supportedLanguages: ['en', 'hi'],
        category: 'Plumbing',
        prerequisites: ['basic-plumbing'],
      );

      expect(course.prerequisites.length, 1);
      expect(course.prerequisites.first, 'basic-plumbing');
      expect(course.supportedLanguages.contains('hi'), true);
    });
  });

  group('Route Names Tests', () {
    test('RouteNames should have valid paths', () {
      expect(RouteNames.home, '/');
      expect(RouteNames.voice, '/voice');
      expect(RouteNames.camera, '/camera');
      expect(RouteNames.documents, '/documents');
      expect(RouteNames.learning, '/learning');
      expect(RouteNames.profile, '/profile');
    });
  });

  group('Asset Paths Tests', () {
    test('AssetPaths should have valid paths', () {
      expect(AssetPaths.images, 'assets/images/');
      expect(AssetPaths.icons, 'assets/icons/');
      expect(AssetPaths.animations, 'assets/animations/');
      expect(AssetPaths.audio, 'assets/audio/');
    });
  });
}
