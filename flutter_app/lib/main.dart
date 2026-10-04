import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const VS3App());

class VS3App extends StatefulWidget {
  const VS3App({super.key});
  @override State<VS3App> createState() => _VS3AppState();
}

class _VS3AppState extends State<VS3App> {
  String baseUrl = const String.fromEnvironment(
    'VS3_API_URL',
    defaultValue: 'https://nse-algo-backend-live-production.up.railway.app',
  );
  String index = 'NIFTY';
  String state = 'CONNECTING';
  Map<String,dynamic> data = {};
  bool loading = false;

  Future<void> refresh() async {
    if (loading) return;
    setState(() { loading=true; state='LOADING'; });
    try {
      final u = Uri.parse('${baseUrl.replaceAll(RegExp(r'/\$'), '')}/v1/ai/context?index=$index');
      final r = await http.get(u).timeout(const Duration(seconds: 10));
      if (r.statusCode >= 200 && r.statusCode < 300) {
        final body=jsonDecode(r.body);
        setState(() { data=body is Map<String,dynamic> ? body : {}; state='LIVE'; });
      } else {
        setState(() => state='API ${r.statusCode}');
      }
    } catch (_) { setState(() => state='OFFLINE'); }
    finally { if(mounted) setState(() => loading=false); }
  }

  @override void initState() { super.initState(); refresh(); }

  @override Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner:false,
    theme: ThemeData.dark(useMaterial3:true).copyWith(
      scaffoldBackgroundColor: const Color(0xFF070B12),
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF22C55E), brightness: Brightness.dark),
    ),
    home: Scaffold(
      appBar: AppBar(
        title: const Text('VS3 • NSE AI Terminal', style: TextStyle(fontWeight: FontWeight.w800)),
        backgroundColor: const Color(0xFF0B111B),
        actions:[IconButton(onPressed:refresh,icon:const Icon(Icons.refresh))],
      ),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: ListView(padding:const EdgeInsets.all(14),children:[
          _panel(Row(children:[
            const Icon(Icons.cloud_done,color:Color(0xFF22C55E)),
            const SizedBox(width:8),
            Expanded(child:Text('$state  •  ${baseUrl.replaceFirst(RegExp(r'https?://'),'')}',
              maxLines:1,overflow:TextOverflow.ellipsis)),
          ])),
          const SizedBox(height:12),
          _panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            const Text('INDEX',style:TextStyle(fontSize:11,color:Colors.white54,fontWeight:FontWeight.bold)),
            const SizedBox(height:8),
            DropdownButtonFormField<String>(
              value:index,
              items:['NIFTY','BANKNIFTY','FINNIFTY','MIDCPNIFTY','SENSEX','BANKEX']
                .map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),
              onChanged:(v){if(v!=null){setState(()=>index=v);refresh();}},
              decoration:const InputDecoration(border:OutlineInputBorder(),isDense:true),
            ),
          ])),
          const SizedBox(height:12),
          Row(children:[
            Expanded(child:_metric('SIGNAL', _pick(['decision','signal','action']) ?? 'WAIT')),
            const SizedBox(width:8),
            Expanded(child:_metric('CONFIDENCE', '${_pick(['confidence','score']) ?? '--'}')),
          ]),
          const SizedBox(height:12),
          _panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            const Text('TRADE PLAN',style:TextStyle(fontSize:12,fontWeight:FontWeight.bold,color:Colors.white70)),
            const SizedBox(height:12),
            Row(children:[
              Expanded(child:_kv('STRIKE',_pick(['strike','entry_strike']) ?? '--')),
              Expanded(child:_kv('ENTRY',_pick(['entry','entry_price']) ?? '--')),
              Expanded(child:_kv('SL',_pick(['sl','stop_loss']) ?? '--')),
              Expanded(child:_kv('TARGET',_pick(['target','target_price']) ?? '--')),
            ]),
          ])),
          const SizedBox(height:12),
          _panel(Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            const Text('LIVE CONTEXT',style:TextStyle(fontWeight:FontWeight.bold,color:Colors.white70)),
            const SizedBox(height:8),
            Text(const JsonEncoder.withIndent('  ').convert(data),
              style:const TextStyle(fontSize:11,color:Colors.white60,fontFamily:'monospace')),
          ])),
        ]),
      ),
    ),
  );

  String? _pick(List<String> keys) {
    for(final k in keys){ final v=data[k]; if(v!=null && v.toString().isNotEmpty) return v.toString(); }
    return null;
  }

  Widget _panel(Widget c)=>Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(
    color:const Color(0xFF0D1521),borderRadius:BorderRadius.circular(16),
    border:Border.all(color:Colors.white10)),child:c);
  Widget _metric(String a,String b)=>_panel(Column(children:[
    Text(a,style:const TextStyle(fontSize:10,color:Colors.white54)),const SizedBox(height:6),
    Text(b,style:const TextStyle(fontSize:22,fontWeight:FontWeight.w900))
  ]));
  Widget _kv(String a,String b)=>Column(children:[
    Text(a,style:const TextStyle(fontSize:9,color:Colors.white45)),const SizedBox(height:5),
    Text(b,style:const TextStyle(fontWeight:FontWeight.w800))
  ]);
}
