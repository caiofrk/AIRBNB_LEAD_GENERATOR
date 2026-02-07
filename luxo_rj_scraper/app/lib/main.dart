import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:ui';
import 'package:intl/intl.dart';
import 'package:flutter/services.dart';

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
      title: 'Leads de Luxo RJ',
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
  String _searchQuery = '';
  String _sortBy = 'score'; // 'score', 'price_asc', 'price_desc', 'newest'
  String _selectedBairro = 'Todos';
  final _currencyFormat = NumberFormat.simpleCurrency(locale: 'pt_BR');

  Stream<List<Map<String, dynamic>>> get _leadsStream =>
      _client.from('leads').stream(primaryKey: ['id']);

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
          child: StreamBuilder<List<Map<String, dynamic>>>(
            stream: _leadsStream,
            builder: (context, snapshot) {
              final allLeads = snapshot.data ?? [];

              // Apply Filtering
              var filteredLeads = allLeads.where((l) {
                final matchSearch =
                    (l['titulo'] ?? '').toLowerCase().contains(
                      _searchQuery.toLowerCase(),
                    ) ||
                    (l['bairro'] ?? '').toLowerCase().contains(
                      _searchQuery.toLowerCase(),
                    );
                final matchBairro =
                    _selectedBairro == 'Todos' ||
                    (l['bairro'] ?? '') == _selectedBairro;
                final isNotContacted = l['contatado'] == false;
                return matchSearch && matchBairro && isNotContacted;
              }).toList();

              // Apply Sorting
              switch (_sortBy) {
                case 'score':
                  filteredLeads.sort(
                    (a, b) =>
                        (b['lux_score'] ?? 0).compareTo(a['lux_score'] ?? 0),
                  );
                  break;
                case 'price_asc':
                  filteredLeads.sort(
                    (a, b) => (a['preco_noite'] ?? 0).compareTo(
                      b['preco_noite'] ?? 0,
                    ),
                  );
                  break;
                case 'price_desc':
                  filteredLeads.sort(
                    (a, b) => (b['preco_noite'] ?? 0).compareTo(
                      a['preco_noite'] ?? 0,
                    ),
                  );
                  break;
                case 'newest':
                  filteredLeads.sort(
                    (a, b) =>
                        (b['criado_em'] ?? '').compareTo(a['criado_em'] ?? ''),
                  );
                  break;
              }

              return RefreshIndicator(
                onRefresh: () async {
                  setState(() {});
                  await Future.delayed(const Duration(seconds: 1));
                },
                color: const Color(0xFF6366F1),
                backgroundColor: const Color(0xFF1E293B),
                child: CustomScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  slivers: [
                    _buildAppBar(),
                    _buildSearchBox(allLeads),
                    _buildStatsSummary(allLeads),
                    _buildLeadsList(snapshot, filteredLeads),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Leads de Luxo',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: -0.5,
                  ),
                ),
                Text(
                  'Mercado do Rio de Janeiro',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.white.withOpacity(0.6),
                  ),
                ),
              ],
            ),
            _buildProfileIcon(),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileIcon() {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF6366F1), Color(0xFFA855F7)],
        ),
        shape: BoxShape.circle,
      ),
      child: const CircleAvatar(
        radius: 20,
        backgroundColor: Color(0xFF1E293B),
        child: Icon(Icons.person_outline, color: Colors.white),
      ),
    );
  }

  Widget _buildSearchBox(List<Map<String, dynamic>> allLeads) {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          child: TextField(
            onChanged: (value) => setState(() => _searchQuery = value),
            style: const TextStyle(color: Colors.white),
            decoration: InputDecoration(
              hintText: 'Buscar imóveis ou bairros...',
              hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
              prefixIcon: Icon(
                Icons.search,
                color: Colors.white.withOpacity(0.3),
              ),
              suffixIcon: IconButton(
                icon: Icon(
                  Icons.tune,
                  color: (_selectedBairro != 'Todos' || _sortBy != 'score')
                      ? const Color(0xFF6366F1)
                      : Colors.white.withOpacity(0.3),
                ),
                onPressed: () => _showFilterSheet(allLeads),
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 15),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatsSummary(List<Map<String, dynamic>> leads) {
    if (leads.isEmpty) return const SliverToBoxAdapter(child: SizedBox());

    final totalValue = leads.fold<double>(
      0,
      (sum, l) => sum + (l['preco_noite'] ?? 0),
    );
    final qualifiedCount = leads
        .where((l) => (l['lux_score'] ?? 0) >= 80)
        .length;
    final totalLeads = leads.length;

    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF6366F1), Color(0xFFA855F7)],
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
              _buildStatItem('Total Leads', '$totalLeads'),
              _buildStatDivider(),
              _buildStatItem('Qualificados', '$qualifiedCount'),
              _buildStatDivider(),
              _buildStatItem('Volume', _formatVolume(totalValue)),
            ],
          ),
        ),
      ),
    );
  }

  String _formatVolume(double value) {
    if (value >= 1000000) return 'R\$ ${(value / 1000000).toStringAsFixed(1)}M';
    if (value >= 1000) return 'R\$ ${(value / 1000).toStringAsFixed(0)}k';
    return 'R\$ ${value.toStringAsFixed(0)}';
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

  Widget _buildLeadsList(
    AsyncSnapshot<List<Map<String, dynamic>>> snapshot,
    List<Map<String, dynamic>> displayLeads,
  ) {
    if (snapshot.connectionState == ConnectionState.waiting) {
      return const SliverFillRemaining(
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (snapshot.hasError) {
      return _buildEmptyState(true);
    }

    final items = displayLeads.isNotEmpty ? displayLeads : _getMockData();

    return SliverPadding(
      padding: const EdgeInsets.all(24),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(
          (context, index) => _buildLeadCard(items[index]),
          childCount: items.length,
        ),
      ),
    );
  }

  List<Map<String, dynamic>> _getMockData() {
    return [
      {
        'id': '1',
        'titulo': 'Cobertura Vista Mar - Ipanema',
        'bairro': 'Ipanema',
        'preco_noite': 4500,
        'lux_score': 98,
        'contatado': false,
        'telefone': '5521999999999',
        'email': 'contato@ipanemarentals.com',
        'link_imovel': 'https://www.airbnb.com.br/rooms/11234567',
      },
      {
        'id': '2',
        'titulo': 'Mansão Moderna com Piscina Privativa',
        'bairro': 'Joá',
        'preco_noite': 8200,
        'lux_score': 95,
        'contatado': false,
        'telefone': '5521999999999',
        'link_imovel': 'https://www.airbnb.com.br/rooms/87654321',
      },
    ];
  }

  Widget _buildLeadCard(Map<String, dynamic> lead) {
    final score = lead['lux_score'] ?? 0;

    return GestureDetector(
      onTap: () => _showLeadDetails(lead),
      child: Container(
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
                          lead['titulo'] ?? 'Imóvel Premium',
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
                          '${lead['bairro'] ?? 'RJ'} • ${_currencyFormat.format(lead['preco_noite'] ?? 0)}',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.white.withOpacity(0.5),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.white24),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildScoreIndicator(int score) {
    final color = score >= 90
        ? Colors.amber
        : score >= 70
        ? Colors.indigoAccent
        : Colors.blueGrey;

    return Container(
      width: 50,
      height: 50,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: color.withOpacity(0.5), width: 2),
      ),
      child: Center(
        child: Text(
          '$score',
          style: TextStyle(fontWeight: FontWeight.bold, color: color),
        ),
      ),
    );
  }

  void _showLeadDetails(Map<String, dynamic> lead) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildDetailSheet(lead),
    );
  }

  Widget _buildDetailSheet(Map<String, dynamic> lead) {
    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      maxChildSize: 0.95,
      builder: (_, controller) => Container(
        decoration: const BoxDecoration(
          color: Color(0xFF0F172A),
          borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
        ),
        child: ListView(
          controller: controller,
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              lead['titulo'] ?? 'Detalhes do Imóvel',
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              '${lead['bairro']} • RJ',
              style: TextStyle(
                fontSize: 16,
                color: Colors.white.withOpacity(0.5),
              ),
            ),
            const SizedBox(height: 24),
            _buildDetailRow(
              Icons.payments_outlined,
              'Preço por noite',
              _currencyFormat.format(lead['preco_noite'] ?? 0),
            ),
            _buildDetailRow(
              Icons.auto_awesome,
              'Score de Luxo',
              '${lead['lux_score']}/100',
            ),
            _buildDetailRow(
              Icons.person_outline,
              'Anfitrião',
              lead['anfitriao'] ?? 'N/A',
            ),
            const SizedBox(height: 32),
            const Text(
              'Ações do Lead',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              Icons.chat_bubble_outline,
              'Conversar no WhatsApp',
              Colors.green,
              () => _openWhatsApp(lead),
            ),
            const SizedBox(height: 12),
            _buildActionButton(
              Icons.email_outlined,
              'Enviar E-mail',
              Colors.blue,
              () => _sendEmail(lead),
            ),
            const SizedBox(height: 12),
            _buildActionButton(
              Icons.travel_explore,
              'Ver no Airbnb',
              Colors.pinkAccent,
              () => _openAirbnb(lead),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: () {
                _markAsContacted(lead['id']);
                Navigator.pop(context);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white10,
                minimumSize: const Size(double.infinity, 56),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Text('Marcar como Contatado'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF6366F1), size: 20),
          const SizedBox(width: 12),
          Text(label, style: TextStyle(color: Colors.white.withOpacity(0.5))),
          const Spacer(),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildActionButton(
    IconData icon,
    String label,
    Color color,
    VoidCallback onTap,
  ) {
    return _AnimatedPress(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            Icon(icon, color: color),
            const SizedBox(width: 12),
            Text(
              label,
              style: TextStyle(color: color, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
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
                  ? 'Erro no Banco de Dados'
                  : 'Nenhum resultado encontrado',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Text(
              isError
                  ? 'Verifique os parâmetros de conexão do Supabase.'
                  : 'Tente buscar por outro bairro ou nome de imóvel.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white.withOpacity(0.5)),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _markAsContacted(dynamic id) async {
    try {
      if (id is String && id.length < 5) return; // Ignore mock data IDs
      await _client.from('leads').update({'contatado': true}).eq('id', id);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Erro: $e')));
    }
  }

  Future<void> _openWhatsApp(Map<String, dynamic> lead) async {
    final phone = lead['telefone'];
    if (phone == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Número de telefone indisponível.')),
      );
      return;
    }
    final num = phone.replaceAll(RegExp(r'[^0-9]'), '');
    final message = Uri.encodeComponent(
      "Olá! Vi seu imóvel ${lead['titulo']} e tenho interesse em seus serviços de gestão de luxo.",
    );
    final url = Uri.parse("https://wa.me/$num?text=$message");
    if (await canLaunchUrl(url))
      await launchUrl(url, mode: LaunchMode.externalApplication);
  }

  Future<void> _sendEmail(Map<String, dynamic> lead) async {
    final email = lead['email'];
    if (email == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('E-mail indisponível.')));
      return;
    }
    final url = Uri.parse(
      "mailto:$email?subject=Interesse%20em%20Gerenciamento%20de%20Imóvel&body=Olá,%20tenho%20interesse%20em%20seu%20imóvel%20${lead['titulo']}",
    );
    if (await canLaunchUrl(url)) await launchUrl(url);
  }

  Future<void> _openAirbnb(Map<String, dynamic> lead) async {
    final link = lead['link_imovel'];
    if (link == null || link.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Link do Airbnb não disponível.')),
      );
      return;
    }
    final url = Uri.parse(link);
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } else {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Não foi possível abrir o link.')),
      );
    }
  }

  void _showFilterSheet(List<Map<String, dynamic>> allLeads) {
    final bairros = [
      'Todos',
      ...allLeads.map((l) => l['bairro']).whereType<String>().toSet(),
    ];

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Container(
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
          ),
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Filtros e Ordenação',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _sortBy = 'score';
                        _selectedBairro = 'Todos';
                      });
                      Navigator.pop(context);
                    },
                    child: const Text('Limpar'),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              const Text(
                'Ordenar por',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.white70,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                children: [
                  _buildFilterChip(
                    'Qualidade',
                    'score',
                    _sortBy,
                    (val) => setState(() => _sortBy = val),
                    setModalState,
                  ),
                  _buildFilterChip(
                    'Menor Preço',
                    'price_asc',
                    _sortBy,
                    (val) => setState(() => _sortBy = val),
                    setModalState,
                  ),
                  _buildFilterChip(
                    'Maior Preço',
                    'price_desc',
                    _sortBy,
                    (val) => setState(() => _sortBy = val),
                    setModalState,
                  ),
                ],
              ),
              const SizedBox(height: 24),
              const Text(
                'Bairros',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.white70,
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 40,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: bairros
                      .map(
                        (b) => Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: _buildFilterChip(
                            b,
                            b,
                            _selectedBairro,
                            (val) => setState(() => _selectedBairro = val),
                            setModalState,
                          ),
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  minimumSize: const Size(double.infinity, 56),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                child: const Text(
                  'Aplicar Filtros',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFilterChip(
    String label,
    String value,
    String current,
    Function(String) onSelect,
    StateSetter setModalState,
  ) {
    final isSelected = value == current;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          onSelect(value);
          setModalState(() {});
        }
      },
      selectedColor: const Color(0xFF6366F1),
      labelStyle: TextStyle(color: isSelected ? Colors.white : Colors.white70),
      backgroundColor: Colors.white.withOpacity(0.05),
      showCheckmark: false,
    );
  }
}

class _AnimatedPress extends StatefulWidget {
  final Widget child;
  final VoidCallback onTap;
  const _AnimatedPress({required this.child, required this.onTap});
  @override
  State<_AnimatedPress> createState() => _AnimatedPressState();
}

class _AnimatedPressState extends State<_AnimatedPress> {
  double _scale = 1.0;
  void _onTapDown(TapDownDetails details) {
    setState(() => _scale = 0.92);
    HapticFeedback.lightImpact();
  }

  void _onTapUp(TapUpDetails details) {
    setState(() => _scale = 1.0);
  }

  void _onTapCancel() {
    setState(() => _scale = 1.0);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: _onTapDown,
      onTapUp: _onTapUp,
      onTapCancel: _onTapCancel,
      onTap: widget.onTap,
      child: AnimatedScale(
        scale: _scale,
        duration: const Duration(milliseconds: 100),
        curve: Curves.easeInOut,
        child: widget.child,
      ),
    );
  }
}
