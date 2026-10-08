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
}
