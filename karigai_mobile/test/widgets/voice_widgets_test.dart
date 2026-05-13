import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:karigai_mobile/presentation/widgets/voice_input_widget.dart';
import 'package:karigai_mobile/presentation/widgets/audio_visualizer_widget.dart';
import 'package:karigai_mobile/presentation/widgets/language_selection_widget.dart';
import 'package:karigai_mobile/presentation/widgets/voice_confirmation_dialog.dart';
import 'package:karigai_mobile/core/localization/app_localizations.dart';

void main() {
  group('Voice Widgets Compilation Tests', () {
    test('VoiceInputWidget can be instantiated', () {
      const widget = VoiceInputWidget(
        selectedLanguage: 'hi',
      );
      expect(widget, isA<VoiceInputWidget>());
    });

    test('AudioVisualizerWidget can be instantiated', () {
      const widget = AudioVisualizerWidget(
        isRecording: true,
        height: 80,
      );
      expect(widget, isA<AudioVisualizerWidget>());
    });

    test('LanguageSelectionWidget can be instantiated', () {
      const widget = LanguageSelectionWidget(
        selectedLanguage: 'hi',
      );
      expect(widget, isA<LanguageSelectionWidget>());
    });

    test('VoiceConfirmationDialog can be instantiated', () {
      const widget = VoiceConfirmationDialog(
        transcribedText: 'Test',
      );
      expect(widget, isA<VoiceConfirmationDialog>());
    });
  });
}

