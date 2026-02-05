import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:ui';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Supabase.initialize(
    url: 'https://vfuhzvyfdivnmrlijtfi.supabase.co',
    anonKey: 'sb_publishable_eLUkti4w2kQDJu6kCQVrpA_4Pr7xt3H',
  );

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Luxury Leads RJ',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        primaryColor: const Color(0xFF6366F1),
        fontFamily: 'Inter',
        useMaterial3: true,
      ),
      home: const DashboardPage(),
    );
  }
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final _client = Supabase.instance.client;

  Stream<List<Map<String, dynamic>>> get _leadsStream => _client
      .from('leads')
      .stream(primaryKey: ['id'])
      .order('lux_score', ascending: false);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
          ),
        ),
        child: SafeArea(
          child: CustomScrollView(
            slivers: [_buildAppBar(), _buildStatsSummary(), _buildLeadsList()],
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Luxury Leads',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: -0.5,
                  ),
                ),
                Text(
                  'Rio de Janeiro Market',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.white.withOpacity(0.6),
                  ),
                ),
              ],
            ),
            Container(
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: IconButton(
                icon: const Icon(
                  Icons.notifications_outlined,
                  color: Colors.white,
                ),
                onPressed: () {},
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsSummary() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [const Color(0xFF6366F1), const Color(0xFFA855F7)],
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF6366F1).withOpacity(0.3),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildStatItem('Total Leads', '124'),
              _buildStatDivider(),
              _buildStatItem('Qualified', '85%'),
              _buildStatDivider(),
              _buildStatItem('Revenue', 'R\$ 2.4M'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        Text(
          label,
          style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.8)),
        ),
      ],
    );
  }

  Widget _buildStatDivider() {
    return Container(
      height: 30,
      width: 1,
      color: Colors.white.withOpacity(0.2),
    );
  }

  Widget _buildLeadsList() {
    return StreamBuilder<List<Map<String, dynamic>>>(
      stream: _leadsStream,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const SliverFillRemaining(
            child: Center(child: CircularProgressIndicator()),
          );
        }

        final dbLeads = snapshot.data ?? [];
        final activeLeads = dbLeads
            .where((l) => l['contatado'] == false)
            .toList();

        // High-end Preview Data if no real leads exist yet
        final displayLeads = activeLeads.isNotEmpty
            ? activeLeads
            : [
                {
                  'id': '1',
                  'titulo': 'Penthouse Ocean View - Ipanema',
                  'bairro': 'Ipanema',
                  'preco_noite': 4500,
                  'lux_score': 98,
                  'contatado': false,
                  'telefone': '5521999999999',
                },
                {
                  'id': '2',
                  'titulo': 'Modern Mansion with Private Pool',
                  'bairro': 'Joá',
                  'preco_noite': 8200,
                  'lux_score': 95,
                  'contatado': false,
                  'telefone': '5521999999999',
                },
                {
                  'id': '3',
                  'titulo': 'Designer Loft near Copacabana',
                  'bairro': 'Copacabana',
                  'preco_noite': 1200,
                  'lux_score': 82,
                  'contatado': false,
                  'telefone': '5521999999999',
                },
              ];

        if (snapshot.hasError) {
          return _buildEmptyState(true);
        }

        return SliverPadding(
          padding: const EdgeInsets.all(24),
          sliver: SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) => _buildLeadCard(displayLeads[index]),
              childCount: displayLeads.length,
            ),
          ),
        );
      },
    );
  }

  Widget _buildLeadCard(Map<String, dynamic> lead) {
    final score = lead['lux_score'] ?? 0;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                _buildScoreIndicator(score),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        lead['titulo'] ?? 'Premium Property',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${lead['bairro'] ?? 'RJ'} • R\$ ${lead['preco_noite']}/night',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.white.withOpacity(0.5),
                        ),
                      ),
                    ],
                  ),
                ),
                _buildActionButtons(lead),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildScoreIndicator(int score) {
    return Container(
      width: 50,
      height: 50,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: score > 80 ? Colors.amber : Colors.blue.withOpacity(0.5),
          width: 2,
        ),
      ),
      child: Center(
        child: Text(
          '$score',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: score > 80 ? Colors.amber : Colors.blue,
          ),
        ),
      ),
    );
  }

  Widget _buildActionButtons(Map<String, dynamic> lead) {
    return Row(
      children: [
        IconButton(
          onPressed: () => _openWhatsApp(lead),
          icon: const Icon(Icons.chat, color: Colors.greenAccent),
        ),
        IconButton(
          onPressed: () => _markAsContacted(lead['id']),
          icon: const Icon(
            Icons.check_circle_outline,
            color: Color(0xFF6366F1),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState(bool isError) {
    return SliverFillRemaining(
      hasScrollBody: false,
      child: Padding(
        padding: const EdgeInsets.all(40.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isError ? Icons.cloud_off : Icons.auto_awesome,
              size: 80,
              color: Colors.white.withOpacity(0.2),
            ),
            const SizedBox(height: 24),
            Text(
              isError
                  ? 'Database Connection Required'
                  : 'Waiting for New Leads',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              isError
                  ? 'Please ensure you have run the setup_db.py SQL in your Supabase Editor.'
                  : 'The market is quiet right now. Run the scraper to find new opportunities in RJ.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: Colors.white.withOpacity(0.5),
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: () => setState(() {}),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                  vertical: 16,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Text('Retry Connection'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _markAsContacted(dynamic id) async {
    try {
      await _client.from('leads').update({'contatado': true}).eq('id', id);
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  Future<void> _openWhatsApp(Map<String, dynamic> lead) async {
    final phone = lead['telefone'];
    if (phone == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No phone number available for this lead.'),
        ),
      );
      return;
    }

    final num = phone.replaceAll(RegExp(r'[^0-9]'), '');
    final message = Uri.encodeComponent(
      "Hello! I saw your property ${lead['titulo']} and am interested in your luxury management services.",
    );
    final url = Uri.parse("https://wa.me/$num?text=$message");

    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }
}
