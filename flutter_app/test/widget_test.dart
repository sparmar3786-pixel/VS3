import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vs3_terminal/main.dart';

void main() {
  testWidgets('NSE-AI-TERMINAL launches with core branding', (tester) async {
    await tester.pumpWidget(const FinalTerminalDesign());
    await tester.pumpAndSettle();

    expect(find.text('NSE-AI-TERMINAL'), findsWidgets);
    expect(find.text('Smart Analysis • Disciplined Decisions'), findsOneWidget);
    expect(find.text('Run60 + Run93'), findsOneWidget);
    expect(find.text('377 Modules'), findsOneWidget);
    expect(find.text('6-Layer AI'), findsOneWidget);
  });
  testWidgets('Login screen exposes real Angel connect controls', (tester) async {
    await tester.pumpWidget(const FinalTerminalDesign());
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2. Login / Authentication'));
    await tester.pumpAndSettle();

    expect(find.text('Client ID'), findsOneWidget);
    expect(find.text('PIN'), findsOneWidget);
    expect(find.text('TOTP'), findsOneWidget);
    expect(find.text('CONNECT ANGEL ONE'), findsOneWidget);
    expect(find.text('NSE MCP'), findsOneWidget);
  });
}

// CI smoke-test file intentionally kept simple for release APK verification.
