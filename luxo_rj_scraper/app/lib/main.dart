import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:ui';
import 'package:intl/intl.dart';
import 'package:flutter/services.dart';
import 'dart:convert';

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
      title: 'Zai Lead Generator',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        primaryColor: const Color(0xFF6366F1),
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
  final Set<String> _selectedHostIds = {};
  bool _isSelectionMode = false;
  String _pipelineFilter =
      'Todos'; // 'Todos', 'Novo', 'Contatado', 'Respondeu', 'Interessado', 'Venda'

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
                    ) ||
                    (l['anfitriao'] ?? '').toLowerCase().contains(
                      _searchQuery.toLowerCase(),
                    );
                final matchBairro =
                    _selectedBairro == 'Todos' ||
                    (l['bairro'] ?? '') == _selectedBairro;
                final isNotContacted = l['contatado'] != true;

                final badges = l['badges'] as List? ?? [];
                String status = 'Novo';
                for (var b in badges) {
                  if (b.toString().startsWith('status:')) {
                    status = b.toString().split(':').last;
                  }
                }
                final matchPipeline =
                    _pipelineFilter == 'Todos' || status == _pipelineFilter;

                return matchSearch &&
                    matchBairro &&
                    isNotContacted &&
                    matchPipeline;
              }).toList();

              // 3. APPLY "THE EQUATION" (Luxury Rate) - OPTIMIZED
              int N = allLeads.length;
              if (N > 0) {
                // Pre-calculate ranks for all prices for ALL leads to fix Stats
                List<double> allPrices = allLeads
                    .map((l) => (l['preco_noite'] as num?)?.toDouble() ?? 0.0)
                    .toList();
                allPrices.sort((a, b) => b.compareTo(a));

                final Map<double, int> priceToRank = {};
                for (int i = 0; i < allPrices.length; i++) {
                  if (!priceToRank.containsKey(allPrices[i])) {
                    priceToRank[allPrices[i]] = i + 1;
                  }
                }

                // Apply to ALL leads first (for Stats)
                for (var l in allLeads) {
                  final price = (l['preco_noite'] as num?)?.toDouble() ?? 0.0;
                  int rank = priceToRank[price] ?? N;
                  l['relative_score'] = ((N - rank + 1) / N) * 100.0;
                }

                // Also ensure filteredLeads has it (they are refs to same maps)
              }

              // Apply Sorting (using normalized score)
              switch (_sortBy) {
                case 'score':
                  filteredLeads.sort(
                    (a, b) => (b['relative_score'] as double).compareTo(
                      a['relative_score'] as double,
                    ),
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
                    (a, b) => (b['created_at'] ?? b['criado_em'] ?? '')
                        .compareTo(a['created_at'] ?? a['criado_em'] ?? ''),
                  );
                  break;
              }

              // Deduplicate by host — show best listing per host
              final Map<String, List<Map<String, dynamic>>> hostGroups = {};
              final List<Map<String, dynamic>> ungrouped = [];
              for (var l in filteredLeads) {
                final host = l['anfitriao'] as String?;
                if (host != null &&
                    host.isNotEmpty &&
                    host != 'Consultar Perfil') {
                  hostGroups.putIfAbsent(host, () => []).add(l);
                } else {
                  ungrouped.add(l);
                }
              }

              // For each host group, pick the best-scored listing as representative
              final List<Map<String, dynamic>> dedupedLeads = [];
              for (var entry in hostGroups.entries) {
                final listings = entry.value;
                // Sort by relative_score descending, pick best
                listings.sort(
                  (a, b) => ((b['relative_score'] as num?) ?? 0).compareTo(
                    (a['relative_score'] as num?) ?? 0,
                  ),
                );
                final representative = Map<String, dynamic>.from(
                  listings.first,
                );
                representative['_grouped_count'] = listings.length;
                representative['_grouped_listings'] = listings;
                dedupedLeads.add(representative);
              }
              // Add ungrouped leads
              for (var l in ungrouped) {
                final rep = Map<String, dynamic>.from(l);
                rep['_grouped_count'] = 1;
                dedupedLeads.add(rep);
              }

              // Re-sort deduped list
              switch (_sortBy) {
                case 'score':
                  dedupedLeads.sort(
                    (a, b) => ((b['relative_score'] as num?) ?? 0).compareTo(
                      (a['relative_score'] as num?) ?? 0,
                    ),
                  );
                  break;
                case 'price_asc':
                  dedupedLeads.sort(
                    (a, b) => (a['preco_noite'] ?? 0).compareTo(
                      b['preco_noite'] ?? 0,
                    ),
                  );
                  break;
                case 'price_desc':
                  dedupedLeads.sort(
                    (a, b) => (b['preco_noite'] ?? 0).compareTo(
                      a['preco_noite'] ?? 0,
                    ),
                  );
                  break;
                case 'newest':
                  dedupedLeads.sort(
                    (a, b) => (b['created_at'] ?? b['criado_em'] ?? '')
                        .compareTo(a['created_at'] ?? a['criado_em'] ?? ''),
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
                    _buildQuickSortBar(),
                    _buildLeadsList(snapshot, dedupedLeads),
                  ],
                ),
              );
            },
          ),
        ),
      ),
      floatingActionButton: _isSelectionMode && _selectedHostIds.isNotEmpty
          ? StreamBuilder<List<Map<String, dynamic>>>(
              stream: _leadsStream,
              builder: (context, snapshot) {
                final allLeads = snapshot.data ?? [];
                var filtered = allLeads.where((l) {
                  final matchSearch =
                      (l['titulo'] ?? '').toLowerCase().contains(
                        _searchQuery.toLowerCase(),
                      ) ||
                      (l['bairro'] ?? '').toLowerCase().contains(
                        _searchQuery.toLowerCase(),
                      ) ||
                      (l['anfitriao'] ?? '').toLowerCase().contains(
                        _searchQuery.toLowerCase(),
                      );
                  final matchBairro =
                      _selectedBairro == 'Todos' ||
                      (l['bairro'] ?? '') == _selectedBairro;
                  final isNotContacted = l['contatado'] != true;
                  return matchSearch && matchBairro && isNotContacted;
                }).toList();

                return FloatingActionButton.extended(
                  onPressed: () => _showMassMessageSheet(filtered),
                  icon: const Icon(Icons.send, color: Colors.white),
                  label: Text('Mensagem (${_selectedHostIds.length})'),
                  backgroundColor: const Color(0xFF6366F1),
                );
              },
            )
          : null,
    );
  }

  void _showMassMessageSheet(List<Map<String, dynamic>> allLeads) {
    final selectedLeads = allLeads
        .where((l) => _selectedHostIds.contains(l['id']))
        .toList();
    final TextEditingController _msgController = TextEditingController(
      text:
          "Olá! Notei seu perfil e gostaria de conversar sobre consultoria para gestão de imóveis de luxo no Rio.",
    );

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.75,
        decoration: const BoxDecoration(
          color: Color(0xFF0F172A),
          borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
        ),
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Mensagem em Massa',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close, color: Colors.white54),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Enviando para ${selectedLeads.length} contatos selecionados.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Template da Mensagem',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.white70,
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _msgController,
              maxLines: 5,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                filled: true,
                fillColor: Colors.white.withOpacity(0.05),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const Spacer(),
            ElevatedButton(
              onPressed: () async {
                Navigator.pop(context);

                int sent = 0;
                for (var lead in selectedLeads) {
                  sent++;
                  final link = lead['link_imovel'];
                  if (link != null) {
                    final url = Uri.parse(link);
                    if (await canLaunchUrl(url)) {
                      await launchUrl(
                        url,
                        mode: LaunchMode.externalApplication,
                      );
                    }
                  }
                  await Future.delayed(const Duration(milliseconds: 500));
                }

                setState(() {
                  _isSelectionMode = false;
                  _selectedHostIds.clear();
                });

                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        'Iniciando envio para $sent hosts no Airbnb...',
                      ),
                    ),
                  );
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                minimumSize: const Size(double.infinity, 56),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Text(
                'Disparar Seqüência',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickSortBar() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            _buildSortButton('Luxury Score', 'score', Icons.auto_awesome),
            _buildSortButton('Preço', 'price_desc', Icons.payments_outlined),
            _buildSortButton('Data/Hora', 'newest', Icons.schedule),
          ],
        ),
      ),
    );
  }

  Widget _buildSortButton(String label, String value, IconData icon) {
    final bool isActive = _sortBy == value;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _sortBy = value);
          HapticFeedback.lightImpact();
        },
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 4),
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isActive
                ? const Color(0xFF6366F1)
                : Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isActive ? Colors.white24 : Colors.white.withOpacity(0.1),
            ),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                size: 18,
                color: isActive ? Colors.white : Colors.white70,
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                  color: isActive ? Colors.white : Colors.white70,
                ),
              ),
            ],
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
                Row(
                  children: [
                    const Text(
                      'Zai',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: Colors.white, // Added color for visibility
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white12,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'v2.3.2',
                        style: TextStyle(fontSize: 10, color: Colors.white38),
                      ),
                    ),
                  ],
                ),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Text(
                    'Inteligência Imobiliária | powered by zaibatsu.tec',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.white.withOpacity(0.5),
                    ),
                  ),
                ),
              ],
            ),
            _buildSelectionToggle(),
          ],
        ),
      ),
    );
  }

  Widget _buildSelectionToggle() {
    return IconButton(
      onPressed: () {
        setState(() {
          _isSelectionMode = !_isSelectionMode;
          if (!_isSelectionMode) _selectedHostIds.clear();
        });
      },
      icon: Icon(
        _isSelectionMode ? Icons.close : Icons.checklist_rtl,
        color: _isSelectionMode ? Colors.pinkAccent : Colors.white70,
        size: 28,
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
    // Use relative_score >= 80 for Qualified as it's what's shown in UI
    final qualifiedCount = leads
        .where((l) => (l['relative_score'] ?? 0.0) >= 80)
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
    final double score = (lead['relative_score'] as num?)?.toDouble() ?? 0.0;
    final timeAgo = _formatTimeAgo(lead['criado_em'] ?? lead['created_at']);

    return _AnimatedPress(
      onTap: () {
        if (_isSelectionMode) {
          setState(() {
            if (_selectedHostIds.contains(lead['id'])) {
              _selectedHostIds.remove(lead['id']);
            } else {
              _selectedHostIds.add(lead['id']);
            }
          });
        } else {
          _showLeadDetails(lead);
        }
      },
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
                  if (_isSelectionMode)
                    Checkbox(
                      value: _selectedHostIds.contains(lead['id']),
                      onChanged: (val) {
                        setState(() {
                          if (val == true) {
                            _selectedHostIds.add(lead['id']);
                          } else {
                            _selectedHostIds.remove(lead['id']);
                          }
                        });
                      },
                      activeColor: const Color(0xFF6366F1),
                      side: const BorderSide(color: Colors.white30),
                    ),
                  const SizedBox(width: 12),
                  _buildScoreIndicator(score),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                lead['anfitriao'] ?? lead['titulo'] ?? 'Lead',
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Text(
                              '${lead['bairro'] ?? 'RJ'} • ${_currencyFormat.format(lead['preco_noite'] ?? 0)}',
                              style: TextStyle(
                                fontSize: 13,
                                color: Colors.white.withOpacity(0.5),
                              ),
                            ),
                            if (lead['cleanliness_gap'] != null) ...[
                              const SizedBox(width: 8),
                              const Icon(
                                Icons.warning_amber_rounded,
                                size: 14,
                                color: Colors.orange,
                              ),
                            ],
                            const Spacer(),
                            if ((lead['host_portfolio_size'] ?? 1) > 1)
                              Container(
                                margin: const EdgeInsets.only(left: 6),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: Colors.greenAccent.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  '${lead['host_portfolio_size']} imóveis',
                                  style: TextStyle(
                                    fontSize: 9,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.greenAccent.withOpacity(0.9),
                                  ),
                                ),
                              ),
                            if (timeAgo.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(left: 6),
                                child: Text(
                                  timeAgo,
                                  style: TextStyle(
                                    fontSize: 10,
                                    color: Colors.white.withOpacity(0.3),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  _isSelectionMode
                      ? const SizedBox.shrink()
                      : const Icon(
                          Icons.chevron_right,
                          color: Colors.white24,
                          size: 20,
                        ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  String _formatTimeAgo(dynamic timestamp) {
    if (timestamp == null) return '';
    try {
      final DateTime date = timestamp is DateTime
          ? timestamp
          : DateTime.parse(timestamp.toString()).toLocal();
      final diff = DateTime.now().difference(date);

      if (diff.inDays > 7) return '${DateFormat('dd/MM').format(date)}';
      if (diff.inDays > 0) return '${diff.inDays}d atrás';
      if (diff.inHours > 0) return '${diff.inHours}h atrás';
      if (diff.inMinutes > 0) return '${diff.inMinutes}m atrás';
      return 'Agora';
    } catch (e) {
      return '';
    }
  }

  Widget _buildScoreIndicator(double score) {
    final color = score >= 90.0
        ? Colors.amber
        : score >= 60.0
        ? Colors.indigoAccent
        : Colors.blueGrey;

    return Container(
      width: 54,
      height: 54,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: color.withOpacity(0.5), width: 2),
      ),
      child: Center(
        child: Text(
          score.toStringAsFixed(1),
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: color,
            fontSize: score >= 100 ? 10 : 12,
          ),
        ),
      ),
    );
  }

  void _showLeadDetails(Map<String, dynamic> initialLead) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _buildReactiveDetailSheet(
        initialLead['id'],
        initialScore: initialLead['relative_score'],
        groupedListings: initialLead['_grouped_listings'],
      ),
    );
  }

  Map<String, dynamic> _parseAIIntel(Map<String, dynamic> lead) {
    try {
      String? raw = lead['ai_report'];
      // Fallback: Check in description
      if (raw == null && lead['descricao'] != null) {
        final desc = lead['descricao'] as String;
        if (desc.contains('--- AI_INTEL_JSON ---')) {
          raw = desc
              .split('--- AI_INTEL_JSON ---')
              .last
              .split('---')
              .first
              .trim();
        }
      }
      if (raw != null) return jsonDecode(raw);
    } catch (_) {}
    return {};
  }

  Map<String, dynamic> _parseContactExtras(Map<String, dynamic> lead) {
    try {
      if (lead['descricao'] != null) {
        final desc = lead['descricao'] as String;
        if (desc.contains('--- CONTACT_INFO_JSON ---')) {
          final raw = desc
              .split('--- CONTACT_INFO_JSON ---')
              .last
              .split('---')
              .first
              .trim();
          return jsonDecode(raw);
        }
      }
    } catch (_) {}
    return {};
  }

  Widget _buildReactiveDetailSheet(
    dynamic leadId, {
    double? initialScore,
    List<Map<String, dynamic>>? groupedListings,
  }) {
    return StreamBuilder<List<Map<String, dynamic>>>(
      stream: _client.from('leads').stream(primaryKey: ['id']).eq('id', leadId),
      builder: (context, snapshot) {
        if (!snapshot.hasData || snapshot.data!.isEmpty) {
          return Container(
            height: 400,
            decoration: const BoxDecoration(
              color: Color(0xFF0F172A),
              borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
            ),
            child: const Center(child: CircularProgressIndicator()),
          );
        }
        final lead = snapshot.data!.first;
        return _buildDetailContent(
          lead,
          relativeScore: initialScore,
          groupedListings: groupedListings,
        );
      },
    );
  }

  String _getLeadStatus(Map<String, dynamic> lead) {
    final badges = lead['badges'] as List? ?? [];
    for (var b in badges) {
      if (b.toString().startsWith('status:')) {
        return b.toString().split(':').last;
      }
    }
    return 'Novo';
  }

  Future<void> _updateLeadStatus(
    Map<String, dynamic> lead,
    String newStatus,
  ) async {
    final List<dynamic> currentBadges = List.from(lead['badges'] ?? []);
    currentBadges.removeWhere((b) => b.toString().startsWith('status:'));
    currentBadges.add('status:$newStatus');

    // Also sync the old 'contatado' boolean for backward compat
    final bool isContacted = [
      'Contatado',
      'Respondeu',
      'Interessado',
      'Venda',
    ].contains(newStatus);

    await _client
        .from('leads')
        .update({'badges': currentBadges, 'contatado': isContacted})
        .eq('id', lead['id']);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Status atualizado para $newStatus'),
          duration: const Duration(seconds: 1),
        ),
      );
    }
  }

  Widget _buildDetailContent(
    Map<String, dynamic> lead, {
    double? relativeScore,
    List<Map<String, dynamic>>? groupedListings,
  }) {
    final aiIntel = _parseAIIntel(lead);
    final double aiLuxScore = (aiIntel['luxury'] as num? ?? 0.0) * 100.0;
    final displayScore = aiLuxScore > 0 ? aiLuxScore : (relativeScore ?? 0.0);
    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      maxChildSize: 0.95,
      builder: (_, controller) => Container(
        decoration: const BoxDecoration(
          color: Color(0xFF0F172A),
          borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
        ),
        child: RefreshIndicator(
          onRefresh: () async {
            setState(() {}); // Triggers a stream re-subscription
            await Future.delayed(const Duration(milliseconds: 500));
          },
          child: ListView(
            controller: controller,
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 48),
            physics: const AlwaysScrollableScrollPhysics(),
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
              const Text(
                'Status do Funil',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.white38,
                ),
              ),
              const SizedBox(height: 12),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children:
                      [
                        'Novo',
                        'Contatado',
                        'Respondeu',
                        'Interessado',
                        'Venda',
                      ].map((s) {
                        final currentStatus = _getLeadStatus(lead);
                        final isSelected = s == currentStatus;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: ChoiceChip(
                            label: Text(
                              s,
                              style: const TextStyle(fontSize: 12),
                            ),
                            selected: isSelected,
                            onSelected: (selected) {
                              if (selected) _updateLeadStatus(lead, s);
                            },
                            selectedColor: const Color(0xFF6366F1),
                            labelStyle: TextStyle(
                              color: isSelected ? Colors.white : Colors.white60,
                            ),
                            backgroundColor: Colors.white.withOpacity(0.05),
                            showCheckmark: false,
                          ),
                        );
                      }).toList(),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                lead['anfitriao'] ?? 'Host Desconhecido',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                lead['titulo'] ?? 'Imóvel',
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.white.withOpacity(0.6),
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                '${lead['bairro']} • RJ',
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.white.withOpacity(0.35),
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
                'Classificação IA (Luxo)',
                '${displayScore.toStringAsFixed(1)}%',
              ),
              _buildDetailRow(
                Icons.person_outline,
                'Anfitrião',
                lead['anfitriao'] ?? 'N/A',
              ),
              const SizedBox(height: 32),
              // Superhost & Portfolio Section
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Sobre o Anfitrião',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  if (lead['badges']?.contains("Superhost") ?? false)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.pink.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.pink.withOpacity(0.3)),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.verified, color: Colors.pink, size: 14),
                          SizedBox(width: 4),
                          Text(
                            'SUPERHOST',
                            style: TextStyle(
                              color: Colors.pink,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              _buildDetailRow(
                Icons.business_center_outlined,
                'Fator de Escala',
                '${lead['host_portfolio_size'] ?? 1} imóvel(is)',
              ),
              ...() {
                final portfolioSize = lead['host_portfolio_size'] ?? 1;
                if (portfolioSize > 1) {
                  return [
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.03),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: Colors.greenAccent.withOpacity(0.15),
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.apartment,
                            color: Colors.greenAccent.withOpacity(0.7),
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '$portfolioSize imóveis gerenciados',
                            style: TextStyle(
                              color: Colors.greenAccent.withOpacity(0.9),
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (groupedListings != null &&
                        groupedListings.length > 1) ...[
                      const SizedBox(height: 16),
                      const Text(
                        'Portfólio do Anfitrião',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white70,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...groupedListings.map((listing) {
                        final isCurrent = listing['id'] == lead['id'];
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isCurrent
                                ? const Color(0xFF6366F1).withOpacity(0.1)
                                : Colors.white.withOpacity(0.02),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isCurrent
                                  ? const Color(0xFF6366F1).withOpacity(0.3)
                                  : Colors.white.withOpacity(0.05),
                            ),
                          ),
                          child: InkWell(
                            onTap: () => _openAirbnb(listing),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        listing['titulo'] ?? 'Sem título',
                                        style: TextStyle(
                                          fontSize: 13,
                                          fontWeight: isCurrent
                                              ? FontWeight.bold
                                              : FontWeight.normal,
                                          color: isCurrent
                                              ? Colors.white
                                              : Colors.white70,
                                        ),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        '${listing['bairro']} • ${_currencyFormat.format(listing['preco_noite'] ?? 0)}',
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: Colors.white.withOpacity(0.4),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                if (isCurrent)
                                  const Icon(
                                    Icons.check_circle,
                                    color: Color(0xFF6366F1),
                                    size: 16,
                                  )
                                else
                                  const Icon(
                                    Icons.arrow_forward_ios,
                                    color: Colors.white24,
                                    size: 12,
                                  ),
                              ],
                            ),
                          ),
                        );
                      }).toList(),
                    ],
                  ];
                }
                return <Widget>[];
              }(),

              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Inteligência de Vendas',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  if (lead['intelligence_status'] == 'ready')
                    const Icon(
                      Icons.check_circle,
                      color: Colors.green,
                      size: 20,
                    )
                  else if (lead['intelligence_status'] == 'pending')
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.amber,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              if (lead['intelligence_status'] == 'ready') ...[
                if (lead['cleanliness_gap'] != null)
                  _buildIntelligenceCard(
                    Icons.warning_amber_rounded,
                    'Gap de Limpeza Encontrado',
                    lead['cleanliness_gap'],
                    Colors.orange,
                  ),
                if (lead['maintenance_items'] != null &&
                    (lead['maintenance_items'] as List).isNotEmpty)
                  _buildIntelligenceCard(
                    Icons.build_circle_outlined,
                    'Manutenção Crítica',
                    (lead['maintenance_items'] as List).join(', '),
                    Colors.blueAccent,
                  ),
                _buildIntelligenceCard(
                  Icons.business_center_outlined,
                  'Fator de Escala',
                  'Host possui ${lead['host_portfolio_size'] ?? 1} imóvel(is)',
                  Colors.greenAccent,
                ),
                const SizedBox(height: 8),
                Center(
                  child: TextButton.icon(
                    onPressed: () => _requestIntelligence(lead['id']),
                    icon: const Icon(
                      Icons.refresh,
                      size: 16,
                      color: Colors.white38,
                    ),
                    label: const Text(
                      'Re-scrape',
                      style: TextStyle(color: Colors.white38, fontSize: 12),
                    ),
                  ),
                ),
              ] else
                _buildActionButton(
                  Icons.analytics_outlined,
                  lead['intelligence_status'] == 'pending'
                      ? 'Análise em Fila...'
                      : 'Iniciar Scrape',
                  Colors.amber,
                  lead['intelligence_status'] == 'pending'
                      ? () {}
                      : () => _requestIntelligence(lead['id']),
                ),
              const SizedBox(height: 32),
              const Text(
                'Ações do Lead',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              _buildActionButton(
                Icons.travel_explore,
                'Mensagem no Airbnb',
                Colors.pinkAccent,
                () => _openAirbnb(lead),
              ),
              const SizedBox(height: 12),
              _buildActionButton(
                Icons.search,
                'Pesquisar Contato',
                Colors.blue,
                () => _searchHostContact(lead),
              ),
              const SizedBox(height: 12),
              if (lead['telefone'] != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _buildActionButton(
                    Icons.chat_bubble_outline,
                    'Conversar no WhatsApp',
                    Colors.green,
                    () => _openWhatsApp(lead),
                  ),
                ),
              if (lead['email'] != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _buildActionButton(
                    Icons.email_outlined,
                    'Enviar E-mail',
                    Colors.orange,
                    () => _sendEmail(lead),
                  ),
                ),
              Builder(
                builder: (context) {
                  final extras = _parseContactExtras(lead);
                  return Column(
                    children: [
                      if (extras['instagram'] != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _buildActionButton(
                            Icons.camera_alt_outlined,
                            'Instagram: ${extras['instagram']}',
                            Colors.purpleAccent,
                            () async {
                              final handle = (extras['instagram'] as String)
                                  .replaceAll('@', '');
                              final url = Uri.parse(
                                'https://instagram.com/$handle',
                              );
                              if (await canLaunchUrl(url)) {
                                await launchUrl(
                                  url,
                                  mode: LaunchMode.externalApplication,
                                );
                              }
                            },
                          ),
                        ),
                      if (extras['website'] != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _buildActionButton(
                            Icons.language,
                            'Website',
                            Colors.tealAccent,
                            () async {
                              final url = Uri.parse(extras['website']);
                              if (await canLaunchUrl(url)) {
                                await launchUrl(
                                  url,
                                  mode: LaunchMode.externalApplication,
                                );
                              }
                            },
                          ),
                        ),
                    ],
                  );
                },
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
              const SizedBox(
                height: 32,
              ), // Safety spacer for Android navigation bars
            ],
          ),
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

  Widget _buildIntelligenceCard(
    IconData icon,
    String title,
    String value,
    Color color,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  value,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.8),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
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

    final aiIntel = _parseAIIntel(lead);
    final waHook = aiIntel['wa_hook'];
    final num = phone.replaceAll(RegExp(r'[^0-9]'), '');

    final String defaultMsg =
        "Olá! Vi seu imóvel ${lead['titulo']} e tenho interesse em seus serviços de gestão de luxo.";
    final String msg = waHook ?? defaultMsg;

    final url = Uri.parse(
      "https://wa.me/$num?text=${Uri.encodeComponent(msg)}",
    );
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
      _promptContact(lead);
    }
  }

  void _promptContact(Map<String, dynamic> lead) {
    if (_getLeadStatus(lead) == 'Novo') {
      ScaffoldMessenger.of(context).hideCurrentSnackBar();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: const Color(0xFF1E293B),
          content: Text(
            'Confirmar contato com ${lead['anfitriao'] ?? 'lead'}?',
            style: const TextStyle(color: Colors.white),
          ),
          action: SnackBarAction(
            label: 'SIM',
            textColor: const Color(0xFF6366F1),
            onPressed: () => _updateLeadStatus(lead, 'Contatado'),
          ),
          duration: const Duration(seconds: 6),
        ),
      );
    }
  }

  Future<void> _sendEmail(Map<String, dynamic> lead) async {
    final email = lead['email'];
    if (email == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('E-mail indisponível.')));
      return;
    }

    final title = lead['titulo'] ?? 'seu imóvel';
    final gap = lead['cleanliness_gap'];
    final maintenance = (lead['maintenance_items'] as List?)?.join(', ') ?? '';

    String body =
        "Olá! Trabalho com limpeza técnica de alto padrão no Rio e notei seu imóvel '$title'.\n\n";

    if (gap != null) {
      body +=
          "Vi em um comentário recente que um hóspede mencionou algo sobre: \"$gap\". ";
      body +=
          "Em locações de luxo, esse tipo de detalhe pode afetar seu status e preço médio. Nós somos especialistas em inspeções de 50 pontos para evitar exatamente isso.\n\n";
    }

    if (maintenance.isNotEmpty) {
      body +=
          "Como seu imóvel possui itens de alta manutenção (como $maintenance), utilizamos produtos específicos que não agridem superfícies nobres.\n\n";
    }

    body +=
        "Gostaria de agendar uma limpeza experimental gratuita ou um orçamento?\n\nNo aguardo,\n[Seu Nome]";

    final subject = Uri.encodeComponent("Serviço Premium para $title");
    final encodedBody = Uri.encodeComponent(body);

    final url = Uri.parse("mailto:$email?subject=$subject&body=$encodedBody");

    if (await canLaunchUrl(url)) {
      await launchUrl(url);
      _promptContact(lead);
    } else {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Não foi possível abrir o app de e-mail.'),
        ),
      );
    }
  }

  Future<void> _searchHostContact(Map<String, dynamic> lead) async {
    final hostName = lead['anfitriao'] ?? lead['titulo'] ?? 'airbnb host';
    final bairro = lead['bairro'] ?? 'Rio de Janeiro';
    final query = Uri.encodeComponent('$hostName $bairro contato telefone');
    final url = Uri.parse('https://www.google.com/search?q=$query');
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
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
      _promptContact(lead);
    } else {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Não foi possível abrir o link.')),
      );
    }
  }

  Future<void> _requestIntelligence(dynamic id) async {
    try {
      await _client
          .from('leads')
          .update({'intelligence_status': 'pending'})
          .eq('id', id);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Solicitação enviada! Rode o scraper no PC para processar.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Erro: $e')));
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
                  _buildFilterChip(
                    'Mais Recente',
                    'newest',
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
              const SizedBox(height: 24),
              const Text(
                'Etapa do Funil',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.white70,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                children:
                    [
                      'Todos',
                      'Novo',
                      'Contatado',
                      'Respondeu',
                      'Interessado',
                      'Venda',
                    ].map((s) {
                      return _buildFilterChip(
                        s,
                        s,
                        _pipelineFilter,
                        (val) => setState(() => _pipelineFilter = val),
                        setModalState,
                      );
                    }).toList(),
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
