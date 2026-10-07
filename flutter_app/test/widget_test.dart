import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vs3_terminal/main.dart';

Future<void> openPage(WidgetTester tester, String label) async {
  await tester.tap(find.byType(PopupMenuButton<String>));
  await tester.pumpAndSettle();
  await tester.tap(find.text(label));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('NSE-AI-TERMINAL launches with dashboard branding', (
    tester,
  ) async {
    await tester.pumpWidget(const FinalTerminalDesign());
    expect(find.text('NSE-AI-TERMINAL'), findsWidgets);
    await openPage(tester, 'Angel One API');
    expect(find.text('Backend URL'), findsWidgets);
  });

  for (final backend in [
    'http://backend.example',
    'backend.example',
    'https:///missing-host',
    'https://[invalid',
    '  https://backend.example///  ',
  ]) {
    testWidgets('guards authenticated requests for $backend', (tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final requests = <http.Request>[];
      await http.runWithClient(
        () async {
          await tester.pumpWidget(const FinalTerminalDesign());
          await openPage(tester, 'Angel One API');
          await tester.enterText(find.byType(TextField).at(0), backend);
          await tester.enterText(
            find.byType(TextField).at(1),
            'test-access-token',
          );
          await tester.tap(find.text('CONNECT ANGEL ONE LIVE'));
          await tester.pumpAndSettle();
          final secure = backend.trim() == 'https://backend.example///';
          expect(
            find.text(
              secure
                  ? 'Angel One connected'
                  : 'Backend URL must use HTTPS with a valid host',
            ),
            findsOneWidget,
          );

          await openPage(tester, 'Charts / Indicators');
          await tester.tap(find.widgetWithText(ChoiceChip, '1m'));
          await tester.pumpAndSettle();

          await openPage(tester, 'Search / Strategy Engine');
          await tester.enterText(find.byType(TextField), 'trend & momentum');
          await tester.pumpAndSettle();

          if (secure) {
            expect(requests.map((r) => r.url.path), [
              '/v1/angel/status',
              '/v1/angel/candles/NIFTY',
              '/v1/angel/candles/NIFTY',
              '/v1/strategies',
            ]);
            for (final request in requests) {
              expect(request.url.scheme, 'https');
              expect(request.url.host, 'backend.example');
              expect(request.headers['x-token'], 'test-access-token');
            }
            expect(requests[2].url.queryParameters['interval'], 'ONE_MINUTE');
            expect(requests.last.url.queryParameters['q'], 'trend & momentum');
          } else {
            expect(requests, isEmpty);
          }
        },
        () => MockClient((request) async {
          requests.add(request);
          return http.Response(
            '{"connected":true,"rows":[],"strategies":[]}',
            200,
          );
        }),
      );
    });
  }
}
