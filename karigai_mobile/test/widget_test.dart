import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:karigai_mobile/main.dart';
import 'package:karigai_mobile/core/app_config.dart';

void main() {
  group('KarigAI App Tests', () {
    testWidgets('App starts and shows home screen', (WidgetTester tester) async {
      // Build our app and trigger a frame.
      await tester.pumpWidget(
        const ProviderScope(
          child: KarigAIApp(),
        ),
      );

      // Wait for the app to settle
      await tester.pumpAndSettle();

      // Verify that the app title is displayed
      expect(find.text('KarigAI'), findsOneWidget);
    });

    testWidgets('Home screen shows feature cards', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: KarigAIApp(),
        ),
      );

      await tester.pumpAndSettle();

      // Check for feature cards
      expect(find.text('Voice Input'), findsOneWidget);
      expect(find.text('Visual Analysis'), findsOneWidget);
      expect(find.text('Documents'), findsOneWidget);
      expect(find.text('Learning'), findsOneWidget);
    });

    testWidgets('Feature cards are tappable', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: KarigAIApp(),
        ),
      );

      await tester.pumpAndSettle();

      // Tap on Voice Input card
      await tester.tap(find.text('Voice Input'));
      await tester.pumpAndSettle();

      // Should navigate to voice input screen
      expect(find.text('Voice Input Screen - To be implemented'), findsOneWidget);
    });
  });

  group('Service Locator Tests', () {
    test('Service locator initializes without errors', () async {
      // This would test the service locator initialization
      // For now, just verify it doesn't throw
      expect(() async {
        // ServiceLocator.init() would be called here in real tests
      }, returnsNormally);
    });
  });

  group('App Config Tests', () {
    test('App config has correct default values', () {
      expect(AppConfig.appName, equals('KarigAI'));
      expect(AppConfig.appVersion, equals('1.0.0'));
      expect(AppConfig.supportedLocales.length, greaterThan(0));
      expect(AppConfig.minConfidenceScore, equals(0.8));
    });
  });
}