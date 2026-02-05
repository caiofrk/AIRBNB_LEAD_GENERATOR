import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await Supabase.initialize(
    url: 'https://<seu-projeto>.supabase.co',
    anonKey: '<sua-anon-key>',
  );

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Growth Imobiliário',
      theme: ThemeData(
        primarySwatch: Colors.indigo,
        useMaterial3: true,
      ),
      home: const LeadsPage(),
    );
  }
}

class LeadsPage extends StatefulWidget {
  const LeadsPage({super.key});

  @override
  State<LeadsPage> createState() => _LeadsPageState();
}

class _LeadsPageState extends State<LeadsPage> {
  // Using stream to listen to changes in real-time
  final _leadsStream = Supabase.instance.client
      .from('leads')
      .stream(primaryKey: ['id'])
      .order('lux_score', ascending: false);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Leads de Luxo - RJ')),
      body: StreamBuilder<List<Map<String, dynamic>>>(
        stream: _leadsStream,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
             // Fallback for demo when no connection
             return const Center(child: Text('Erro na conexão ou sem dados (Demo Mode)'));
          }
          
          final leads = snapshot.data ?? [];
          final activeLeads = leads.where((l) => l['contatado'] == false).toList();
          
          if (activeLeads.isEmpty) {
            return const Center(child: Text('Nenhum lead pendente! 🚀'));
          }

          return ListView.builder(
            itemCount: activeLeads.length,
            itemBuilder: (context, index) {
              final lead = activeLeads[index];
              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Colors.amber,
                    child: Text('${lead['lux_score'] ?? '?'}'),
                  ),
                  title: Text(lead['titulo'] ?? 'Imóvel sem Nome', maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text("${lead['bairro'] ?? 'RJ'} • R\$ ${lead['preco_noite']}"),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                       IconButton(
                        icon: const Icon(Icons.whatsapp, color: Colors.green),
                        onPressed: () => _openWhatsApp(lead),
                      ),
                      IconButton(
                        icon: const Icon(Icons.check_circle, color: Colors.blue),
                        onPressed: () => _markAsContacted(lead['id']),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  Future<void> _markAsContacted(dynamic id) async {
    try {
      await Supabase.instance.client
          .from('leads')
          .update({'contatado': true})
          .eq('id', id);
    } catch(e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erro: $e')));
    }
  }

  Future<void> _openWhatsApp(Map<String, dynamic> lead) async {
    final phone = lead['telefone'];
    if (phone == null) return;
    
    // Simple filter for digits
    final num = phone.replaceAll(RegExp(r'[^0-9]'), ''); 
    final message = Uri.encodeComponent("Olá, tenho interesse no seu imóvel ${lead['titulo']}!");
    final url = Uri.parse("https://wa.me/$num?text=$message");
    
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }
}
