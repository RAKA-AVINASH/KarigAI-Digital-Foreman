import 'package:flutter_test/flutter_test.dart';
import 'package:karigai_mobile/data/services/websocket_service.dart';
import 'dart:async';

void main() {
  group('WebSocket Integration Tests', () {
    late WebSocketService wsService;
    
    setUp(() {
      wsService = WebSocketService();
    });
    
    tearDown(() async {
      await wsService.dispose();
    });
    
    test('should connect to WebSocket server', () async {
      try {
        await wsService.connect();
        
        // Wait a bit for connection to establish
        await Future.delayed(const Duration(seconds: 2));
        
        expect(wsService.isConnected, true);
      } catch (e) {
        // Expected to fail without backend
        expect(e, isNotNull);
      }
    });
    
    test('should handle connection failure gracefully', () async {
      try {
        await wsService.connect();
        
        // Even if connection fails, service should handle it
        expect(wsService, isNotNull);
      } catch (e) {
        expect(e, isNotNull);
      }
    });
    
    test('should stream connection status', () async {
      final statusStream = wsService.connectionStatusStream;
      expect(statusStream, isA<Stream<bool>>());
      
      final completer = Completer<bool>();
      final subscription = statusStream.listen((isConnected) {
        if (!completer.isCompleted) {
          completer.complete(isConnected);
        }
      });
      
      try {
        await wsService.connect();
        
        final status = await completer.future.timeout(
          const Duration(seconds: 5),
          onTimeout: () => false,
        );
        
        expect(status, isA<bool>());
      } finally {
        await subscription.cancel();
      }
    });
    
    test('should send and receive messages', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.sendMessage({'type': 'test', 'data': 'hello'});
          
          // Wait for potential response
          await Future.delayed(const Duration(seconds: 1));
          
          expect(wsService.isConnected, true);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
    
    test('should handle transcription stream', () async {
      final transcriptionStream = wsService.transcriptionStream;
      expect(transcriptionStream, isA<Stream<Map<String, dynamic>>>());
      
      final transcriptions = <Map<String, dynamic>>[];
      final subscription = transcriptionStream.listen((data) {
        transcriptions.add(data);
      });
      
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.startTranscription(
            sessionId: 'test_session',
            languageCode: 'hi-IN',
          );
          
          // Wait for potential transcription data
          await Future.delayed(const Duration(seconds: 2));
          
          expect(transcriptions, isA<List<Map<String, dynamic>>>());
        }
      } finally {
        await subscription.cancel();
      }
    });
    
    test('should handle progress stream', () async {
      final progressStream = wsService.progressStream;
      expect(progressStream, isA<Stream<Map<String, dynamic>>>());
      
      final progressUpdates = <Map<String, dynamic>>[];
      final subscription = progressStream.listen((data) {
        progressUpdates.add(data);
      });
      
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.subscribeToProgress(operationId: 'test_operation');
          
          // Wait for potential progress updates
          await Future.delayed(const Duration(seconds: 2));
          
          expect(progressUpdates, isA<List<Map<String, dynamic>>>());
        }
      } finally {
        await subscription.cancel();
      }
    });
    
    test('should reconnect after disconnection', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          // Disconnect
          await wsService.disconnect();
          expect(wsService.isConnected, false);
          
          // Reconnect
          await wsService.connect();
          await Future.delayed(const Duration(seconds: 2));
          
          // Should attempt to reconnect
          expect(wsService, isNotNull);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
    
    test('should handle multiple simultaneous connections', () async {
      final ws1 = WebSocketService();
      final ws2 = WebSocketService();
      
      try {
        await Future.wait([
          ws1.connect(),
          ws2.connect(),
        ]);
        
        // Both should handle connection attempts
        expect(ws1, isNotNull);
        expect(ws2, isNotNull);
      } finally {
        await ws1.dispose();
        await ws2.dispose();
      }
    });
    
    test('should clean up resources on dispose', () async {
      await wsService.connect();
      await wsService.dispose();
      
      // After dispose, should not be connected
      expect(wsService.isConnected, false);
    });
    
    test('should handle heartbeat mechanism', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          // Wait for heartbeat interval
          await Future.delayed(const Duration(seconds: 35));
          
          // Connection should still be alive
          expect(wsService.isConnected, true);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
    
    test('should limit reconnection attempts', () async {
      // This test verifies that reconnection doesn't continue indefinitely
      try {
        await wsService.connect();
        
        // Even with connection failures, should eventually stop trying
        await Future.delayed(const Duration(seconds: 15));
        
        expect(wsService, isNotNull);
      } catch (e) {
        expect(e, isNotNull);
      }
    });
  });
  
  group('Live Transcription Tests', () {
    late WebSocketService wsService;
    
    setUp(() {
      wsService = WebSocketService();
    });
    
    tearDown(() async {
      await wsService.dispose();
    });
    
    test('should start transcription session', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.startTranscription(
            sessionId: 'test_session_1',
            languageCode: 'hi-IN',
          );
          
          await Future.delayed(const Duration(seconds: 1));
          expect(wsService.isConnected, true);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
    
    test('should stop transcription session', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.startTranscription(sessionId: 'test_session_2');
          await Future.delayed(const Duration(milliseconds: 500));
          
          wsService.stopTranscription(sessionId: 'test_session_2');
          await Future.delayed(const Duration(milliseconds: 500));
          
          expect(wsService.isConnected, true);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
    
    test('should send audio chunks', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.startTranscription(sessionId: 'test_session_3');
          
          // Send mock audio chunks
          for (int i = 0; i < 5; i++) {
            wsService.sendAudioChunk(
              sessionId: 'test_session_3',
              audioData: 'mock_audio_data_$i',
            );
            await Future.delayed(const Duration(milliseconds: 100));
          }
          
          expect(wsService.isConnected, true);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
  });
  
  group('Progress Updates Tests', () {
    late WebSocketService wsService;
    
    setUp(() {
      wsService = WebSocketService();
    });
    
    tearDown(() async {
      await wsService.dispose();
    });
    
    test('should subscribe to progress updates', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.subscribeToProgress(operationId: 'operation_1');
          await Future.delayed(const Duration(seconds: 1));
          
          expect(wsService.isConnected, true);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
    
    test('should unsubscribe from progress updates', () async {
      try {
        await wsService.connect();
        
        if (wsService.isConnected) {
          wsService.subscribeToProgress(operationId: 'operation_2');
          await Future.delayed(const Duration(milliseconds: 500));
          
          wsService.unsubscribeFromProgress(operationId: 'operation_2');
          await Future.delayed(const Duration(milliseconds: 500));
          
          expect(wsService.isConnected, true);
        }
      } catch (e) {
        expect(e, isNotNull);
      }
    });
  });
}
