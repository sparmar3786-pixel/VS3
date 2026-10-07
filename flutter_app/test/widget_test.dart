import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vs3_terminal/main.dart';

void main() {
  testWidgets('NSE-AI-TERMINAL launches with dashboard branding', (tester) async {
    await tester.pumpWidget(const FinalTerminalDesign());
    expect(find.text('NSE-AI-TERMINAL'), findsWidgets);
  });
}
