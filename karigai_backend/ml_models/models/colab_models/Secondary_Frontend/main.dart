import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:record/record.dart'; 
import 'dart:convert';
import 'package:audioplayers/audioplayers.dart'; 
import 'package:path_provider/path_provider.dart'; 
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:image_picker/image_picker.dart'; 
import 'package:crypto/crypto.dart'; 

void main() {
  runApp(const KarigAIApp());
}

class KarigAIApp extends StatelessWidget {
  const KarigAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'KarigAI Final',
      theme: ThemeData(
        primarySwatch: Colors.orange, 
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.grey[50],
      ),
      home: const MainScreen(),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});
  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;
  final String serverUrl = "http://127.0.0.1:8000";
  String selectedLang = 'hi'; 

  @override
  Widget build(BuildContext context) {
    final List<Widget> _screens = [
      VoiceInvoiceScreen(serverUrl: serverUrl, lang: selectedLang, onLangChange: (l) => setState(() => selectedLang = l)),
      VisionRepairScreen(serverUrl: serverUrl, lang: selectedLang),
      LearningScreen(serverUrl: serverUrl, lang: selectedLang, onLangChange: (l) => setState(() => selectedLang = l)),
      DocumentsScreen(serverUrl: serverUrl, lang: selectedLang),
    ];

    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.mic), label: 'Voice Input'),
          NavigationDestination(icon: Icon(Icons.camera_alt), label: 'Visual Analysis'),
          NavigationDestination(icon: Icon(Icons.school), label: 'Learning'),
          NavigationDestination(icon: Icon(Icons.description), label: 'Documents'),
        ],
      ),
    );
  }
}

// ==========================================
// TAB 1: VOICE INVOICE, CONTRACT & CERTIFICATE SCREEN
// ==========================================
class VoiceInvoiceScreen extends StatefulWidget {
  final String serverUrl;
  final String lang;
  final Function(String) onLangChange;
  const VoiceInvoiceScreen({required this.serverUrl, required this.lang, required this.onLangChange, super.key});

  @override
  State<VoiceInvoiceScreen> createState() => _VoiceInvoiceScreenState();
}

class _VoiceInvoiceScreenState extends State<VoiceInvoiceScreen> {
  late final AudioRecorder _audioRecorder;
  late final AudioPlayer _audioPlayer; 
  bool _isRecording = false;
  String _statusText = "Tap Mic & Speak (e.g., 'Make a contract...' or '5 cement bags...' or 'Verify my handloom saree...')";
  
  Map<String, dynamic>? _documentData;
  String? _detectedIntent;
  int? _confidenceScore; 

  // Image variable for certificate
  Uint8List? _certImageBytes;

  String _artisanName = "KarigAI Artisan";
  String _artisanUpiId = "your_mobile_number@upi";
  String _tradeType = "General Artisan";

  final Map<String, String> _languages = {
    'hi': 'Hindi (हिंदी)', 'en': 'English', 'bn': 'Bengali (বাংলা)', 
    'ta': 'Tamil (தமிழ்)', 'te': 'Telugu (తెలుగు)', 'mr': 'Marathi (मराठी)',
    'gu': 'Gujarati (ગુજરાતી)', 'kn': 'Kannada (ಕನ್ನಡ)', 'ml': 'Malayalam (മലയാളം)',
    'ur': 'Urdu (اردو)', 'pa': 'Punjabi (ਪੰਜਾਬੀ)'
  };

  @override
  void initState() {
    super.initState();
    _audioRecorder = AudioRecorder();
    _audioPlayer = AudioPlayer();
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _playBase64Audio(String base64String) async {
    try {
      Uint8List audioBytes = base64Decode(base64String);
      if (kIsWeb) {
        await _audioPlayer.play(BytesSource(audioBytes));
      } else {
        final dir = await getTemporaryDirectory();
        final file = File('${dir.path}/response_voice.mp3');
        await file.writeAsBytes(audioBytes);
        await _audioPlayer.play(DeviceFileSource(file.path));
      }
    } catch (e) { print("Audio Error: $e"); }
  }

  void _showProfileSettings() {
    TextEditingController nameCtrl = TextEditingController(text: _artisanName);
    TextEditingController upiCtrl = TextEditingController(text: _artisanUpiId);
    String tempTrade = _tradeType;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: const Text(" Profile Settings", style: TextStyle(color: Colors.orange)),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: "Your Name / Business Name", prefixIcon: Icon(Icons.person))),
                const SizedBox(height: 10),
                TextField(controller: upiCtrl, decoration: const InputDecoration(labelText: "Your UPI ID (e.g. 9999999999@ybl)", prefixIcon: Icon(Icons.account_balance_wallet))),
                const SizedBox(height: 15),
                DropdownButtonFormField<String>(
                  value: tempTrade,
                  decoration: const InputDecoration(labelText: "Trade / Profession", prefixIcon: Icon(Icons.work)),
                  items: ["General Artisan", "Carpenter", "Tailor/Weaver", "Electrician", "Plumber", "Painter"]
                      .map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                  onChanged: (val) => setDialogState(() => tempTrade = val!),
                ),
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: Colors.orange, foregroundColor: Colors.white),
                onPressed: () {
                  setState(() { _artisanName = nameCtrl.text; _artisanUpiId = upiCtrl.text; _tradeType = tempTrade; });
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Profile Updated!")));
                },
                child: const Text("Save"),
              )
            ],
          );
        }
      ),
    );
  }

  //Certificate Image Picker
  Future<void> _pickCertificateImage() async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery, imageQuality: 50);
    if (image != null) {
      var f = await image.readAsBytes();
      setState(() { _certImageBytes = f; });
    }
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      final path = await _audioRecorder.stop();
      setState(() { _isRecording = false; _statusText = "Analyzing Intent & Processing..."; });
      if (path != null) _uploadAudio(path);
    } else {
      if (await _audioRecorder.hasPermission()) {
        await _audioRecorder.start(const RecordConfig(encoder: AudioEncoder.opus), path: '');
        setState(() { 
          _isRecording = true; 
          _statusText = "Listening..."; 
          _documentData = null; 
          _detectedIntent = null; 
          _confidenceScore = null; 
          _certImageBytes = null; 
        });
      }
    }
  }

  Future<void> _uploadAudio(String path) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('${widget.serverUrl}/transcribe'));
      request.fields['language'] = widget.lang; 
      request.fields['doc_type'] = 'auto'; 

      if (kIsWeb) {
        var bytes = await http.readBytes(Uri.parse(path));
        request.files.add(http.MultipartFile.fromBytes('file', bytes, filename: 'audio.webm'));
      } else {
        var bytes = await File(path).readAsBytes();
        request.files.add(http.MultipartFile.fromBytes('file', bytes, filename: 'audio.m4a'));
      }

      final response = await http.Response.fromStream(await request.send());
      
      if (response.statusCode == 200) {
        final jsonResp = json.decode(response.body);
        setState(() { 
          _statusText = "Done!"; 
          _detectedIntent = jsonResp['detected_intent'];
          _confidenceScore = jsonResp['confidence_score'];
          
          if (_detectedIntent == 'contract') { _documentData = jsonResp['contract_json']; } 
          else if (_detectedIntent == 'certificate') { _documentData = jsonResp['certificate_json']; } 
          else { _documentData = jsonResp['invoice_json']; }
        });
        if (jsonResp['audio_base64'] != null) _playBase64Audio(jsonResp['audio_base64']);
      } else {
        setState(() { _statusText = "Server Error: ${response.statusCode}"; });
      }
    } catch (e) { setState(() { _statusText = "Error: $e"; }); }
  }

  String _generateDigitalSignature(Map<String, dynamic> data) {
    final rawData = jsonEncode(data) + _artisanName + DateTime.now().toIso8601String();
    final bytes = utf8.encode(rawData);
    final digest = sha256.convert(bytes);
    return digest.toString().substring(0, 32); 
  }

  Future<void> _generatePdf() async {
    if (_documentData == null) return;

    pw.Font myFont;
    pw.Font? myFontBold;

    switch (widget.lang) {
      case 'hi': case 'mr': myFont = await PdfGoogleFonts.notoSansDevanagariRegular(); myFontBold = await PdfGoogleFonts.notoSansDevanagariBold(); break;
      case 'bn': myFont = await PdfGoogleFonts.notoSansBengaliRegular(); myFontBold = await PdfGoogleFonts.notoSansBengaliBold(); break;
      case 'ta': myFont = await PdfGoogleFonts.notoSansTamilRegular(); myFontBold = await PdfGoogleFonts.notoSansTamilBold(); break;
      case 'te': myFont = await PdfGoogleFonts.notoSansTeluguRegular(); myFontBold = await PdfGoogleFonts.notoSansTeluguBold(); break;
      case 'gu': myFont = await PdfGoogleFonts.notoSansGujaratiRegular(); myFontBold = await PdfGoogleFonts.notoSansGujaratiBold(); break;
      case 'kn': myFont = await PdfGoogleFonts.notoSansKannadaRegular(); myFontBold = await PdfGoogleFonts.notoSansKannadaBold(); break;
      case 'ml': myFont = await PdfGoogleFonts.notoSansMalayalamRegular(); myFontBold = await PdfGoogleFonts.notoSansMalayalamBold(); break;
      case 'pa': myFont = await PdfGoogleFonts.notoSansGurmukhiRegular(); myFontBold = await PdfGoogleFonts.notoSansGurmukhiBold(); break;
      case 'ur': myFont = await PdfGoogleFonts.notoNastaliqUrduRegular(); myFontBold = myFont; break;
      default: myFont = await PdfGoogleFonts.robotoRegular(); myFontBold = await PdfGoogleFonts.robotoBold();
    }

    final pdf = pw.Document();

    final pageTheme = pw.PageTheme(
      theme: pw.ThemeData.withFont(base: myFont, bold: myFontBold ?? myFont),
      buildBackground: (pw.Context context) {
        return pw.FullPage(
          ignoreMargins: true,
          child: pw.Center(
            child: pw.Transform.rotate(
              angle: 0.5, 
              child: pw.Text('KarigAI Verified', style: pw.TextStyle(color: PdfColors.grey300, fontSize: 60, fontWeight: pw.FontWeight.bold)),
            ),
          ),
        );
      },
    );

    PdfColor brandColor = PdfColors.blue800; 
    if (_tradeType == "Carpenter") brandColor = PdfColors.brown800;
    if (_tradeType == "Tailor/Weaver") brandColor = PdfColors.purple800;
    if (_tradeType == "Electrician") brandColor = PdfColors.amber800;
    if (_tradeType == "Painter") brandColor = PdfColors.teal800;
    if (_tradeType == "Plumber") brandColor = PdfColors.indigo800;

    pdf.addPage(pw.Page(pageTheme: pageTheme, build: (pw.Context context) {
      
      if (_detectedIntent == 'certificate') {
        final signatureHash = _generateDigitalSignature(_documentData!);
        final verifyUrl = "https://karigai.app/verify/$signatureHash"; 

        return pw.Container(
          decoration: pw.BoxDecoration(border: pw.Border.all(color: brandColor, width: 4)),
          padding: const pw.EdgeInsets.all(20),
          child: pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.center,
            mainAxisAlignment: pw.MainAxisAlignment.center,
            children: [
              pw.Text("CERTIFICATE OF AUTHENTICITY", style: pw.TextStyle(fontSize: 28, fontWeight: pw.FontWeight.bold, color: brandColor)),
              pw.SizedBox(height: 10),
              pw.Text("KarigAI Verified & Tamper-Proof", style: pw.TextStyle(fontSize: 12, color: PdfColors.grey600)),
              pw.SizedBox(height: 30),
              
              pw.Text("This document certifies that the product described below is a genuine, handcrafted creation by a verified KarigAI artisan.", textAlign: pw.TextAlign.center, style: pw.TextStyle(fontSize: 14)),
              pw.SizedBox(height: 20),
              
              pw.Container(
                padding: const pw.EdgeInsets.all(15),
                decoration: pw.BoxDecoration(color: PdfColors.grey100, borderRadius: pw.BorderRadius.circular(8)),
                child: pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Text("Product: ${_documentData!['product_name']}", style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold)),
                    pw.SizedBox(height: 10),
                    
                    
                    if (_certImageBytes != null) ...[
                      pw.Center(
                        child: pw.Container(
                          height: 120, 
                          decoration: pw.BoxDecoration(border: pw.Border.all(color: PdfColors.grey400)),
                          child: pw.Image(pw.MemoryImage(_certImageBytes!), fit: pw.BoxFit.contain)
                        )
                      ),
                      pw.SizedBox(height: 15),
                    ],

                    pw.Text("Materials Used: ${_documentData!['material_used']}"),
                    pw.SizedBox(height: 5),
                    pw.Text("Origin/Art Form: ${_documentData!['cultural_origin']}"),
                    pw.SizedBox(height: 5),
                    pw.Text("Process: ${_documentData!['creation_process']}", style: pw.TextStyle(color: PdfColors.grey800)),
                  ]
                )
              ),
              
              pw.SizedBox(height: 30),
              pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                crossAxisAlignment: pw.CrossAxisAlignment.end,
                children: [
                  pw.Column(
                    crossAxisAlignment: pw.CrossAxisAlignment.start,
                    children: [
                      pw.Text("Certified Artisan:", style: pw.TextStyle(fontSize: 12, color: PdfColors.grey600)),
                      pw.Text("$_artisanName", style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold)),
                      pw.Text("$_tradeType", style: pw.TextStyle(fontSize: 14, color: brandColor)),
                      pw.SizedBox(height: 20),
                      pw.Text("Digital Signature (SHA-256):", style: pw.TextStyle(fontSize: 8, color: PdfColors.grey600)),
                      pw.Text(signatureHash, style: pw.TextStyle(fontSize: 10, font: pw.Font.courier())),
                    ]
                  ),
                  pw.Column(
                    children: [
                      pw.Text("Scan to Verify", style: pw.TextStyle(fontSize: 10, fontWeight: pw.FontWeight.bold)),
                      pw.SizedBox(height: 5),
                      pw.BarcodeWidget(barcode: pw.Barcode.qrCode(), data: verifyUrl, width: 80, height: 80),
                    ]
                  )
                ]
              )
            ]
          )
        );
      } 
      else if (_detectedIntent == 'contract') {
        return pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            pw.Center(child: pw.Text("LEGAL AGREEMENT", style: pw.TextStyle(fontSize: 24, fontWeight: pw.FontWeight.bold, color: brandColor))),
            pw.SizedBox(height: 20),
            pw.Text("Title: ${_documentData!['title']}", style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold)),
            pw.SizedBox(height: 10),
            pw.Text("Party A (Contractor): ${_documentData!['party_a']}"),
            pw.Text("Party B (Client): ${_documentData!['party_b']}"),
            pw.Divider(),
            pw.Text("Scope of Work:", style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
            pw.Text("${_documentData!['scope_of_work']}"),
            pw.SizedBox(height: 10),
            pw.Text("Payment Terms:", style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
            pw.Text("${_documentData!['payment_terms']}"),
            pw.SizedBox(height: 10),
            pw.Text("Risk Protection Clauses:", style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
            ...(_documentData!['risk_clauses'] as List).map((clause) => pw.Bullet(text: clause.toString())),
            pw.SizedBox(height: 40),
            pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Text("Sign (Party A): ________________"),
                pw.Text("Sign (Party B): ________________"),
              ]
            )
          ]
        );
      } 
      else {
        final totalAmt = _documentData!['grand_total'].toString();
        final encodedName = Uri.encodeComponent(_artisanName); 
        final upiString = "upi://pay?pa=$_artisanUpiId&pn=$encodedName&am=$totalAmt&cu=INR";

        return pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            pw.Container(
              padding: const pw.EdgeInsets.all(10),
              decoration: pw.BoxDecoration(color: brandColor, borderRadius: const pw.BorderRadius.all(pw.Radius.circular(8))),
              child: pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                children: [
                  pw.Column(
                    crossAxisAlignment: pw.CrossAxisAlignment.start,
                    children: [
                      pw.Text("TAX INVOICE", style: pw.TextStyle(color: PdfColors.white, fontSize: 20, fontWeight: pw.FontWeight.bold)),
                      pw.Text("$_artisanName | Professional $_tradeType", style: pw.TextStyle(color: PdfColors.white, fontSize: 10)),
                    ]
                  ),
                  pw.Text("KarigAI", style: pw.TextStyle(color: PdfColors.white, fontSize: 14, fontStyle: pw.FontStyle.italic)),
                ]
              )
            ),
            pw.SizedBox(height: 20),
            pw.Header(level: 0, child: pw.Text("KarigAI Invoice")),
            pw.Table.fromTextArray(data: <List<String>>[
              <String>['Item', 'Qty', 'Unit', 'Price', 'Total'],
              ...(_documentData!['items'] as List).map((item) => [
                item['name'].toString(), 
                item['qty'].toString(), 
                item['unit'].toString(), 
                item['unit_price'].toString(), 
                item['total_amount'].toString()
              ]),
            ]),
            pw.SizedBox(height: 30),
            pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              crossAxisAlignment: pw.CrossAxisAlignment.end,
              children: [
                pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.center,
                  children: [
                    pw.Text("Scan to Pay via UPI", style: pw.TextStyle(fontSize: 10, color: PdfColors.grey700)),
                    pw.SizedBox(height: 8),
                    pw.BarcodeWidget(barcode: pw.Barcode.qrCode(), data: upiString, width: 80, height: 80),
                  ],
                ),
                pw.Text("Grand Total: INR $totalAmt", style: pw.TextStyle(fontWeight: pw.FontWeight.bold, fontSize: 18)),
              ]
            ),
          ]
        );
      }
    }));
    
    await Printing.layoutPdf(onLayout: (format) async => pdf.save());
  }

  @override
  Widget build(BuildContext context) {
    Color chipBgColor = Colors.grey.shade200;
    Color chipTextColor = Colors.black;
    if (_detectedIntent == 'contract') { chipBgColor = Colors.purple.shade100; chipTextColor = Colors.purple.shade800; }
    else if (_detectedIntent == 'certificate') { chipBgColor = Colors.amber.shade100; chipTextColor = Colors.amber.shade900; }
    else if (_detectedIntent == 'invoice') { chipBgColor = Colors.green.shade100; chipTextColor = Colors.green.shade800; }

    return Scaffold(
      appBar: AppBar(
        title: const Text("KarigAI Voice "),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8.0),
            child: IconButton(
              icon: CircleAvatar(backgroundColor: Colors.orange.shade200, child: const Icon(Icons.person, color: Colors.white)),
              tooltip: 'Profile Settings',
              onPressed: _showProfileSettings,
            ),
          )
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(border: Border.all(color: Colors.orange), borderRadius: BorderRadius.circular(8)),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: widget.lang,
                  isExpanded: true,
                  items: _languages.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
                  onChanged: (val) => widget.onLangChange(val!),
                ),
              ),
            ),
          ),
          
          if (_detectedIntent != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4.0),
              child: Chip(
                backgroundColor: chipBgColor,
                label: Text(
                  " AI Intent: ${_detectedIntent!.toUpperCase()} " + 
                  (_confidenceScore != null ? "($_confidenceScore% Match)" : ""),
                  style: TextStyle(fontWeight: FontWeight.bold, color: chipTextColor)
                ),
              ),
            ),

          Expanded(
            child: _documentData == null 
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.mic_none_outlined, size: 80, color: Colors.orange.shade200),
                      const SizedBox(height: 10),
                      Text(_statusText, style: const TextStyle(fontSize: 16, color: Colors.grey), textAlign: TextAlign.center,),
                    ],
                  ),
                )
              : SingleChildScrollView( 
                  padding: const EdgeInsets.all(12.0),
                  child: Column(
                    children: [
                      Card(
                        elevation: 4,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: _detectedIntent == 'contract' ? _buildContractUI() 
                               : _detectedIntent == 'certificate' ? _buildCertificateUI() 
                               : _buildInvoiceUI(),
                        ),
                      ),
                      const SizedBox(height: 15),
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.picture_as_pdf), 
                          label: Text("Generate ${_detectedIntent!.toUpperCase()} PDF"), 
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade700, foregroundColor: Colors.white),
                          onPressed: _generatePdf
                        ),
                      ),
                      const SizedBox(height: 100), 
                    ],
                  ),
                ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.large(
        onPressed: _toggleRecording,
        backgroundColor: _isRecording ? Colors.red : Colors.orange,
        child: Icon(_isRecording ? Icons.stop : Icons.mic, color: Colors.white),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }


  Widget _buildCertificateUI() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Center(child: Text("CERTIFICATE PREVIEW", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, letterSpacing: 1.2, color: Colors.amber))),
        const Divider(),
        
        //  Image Preview and Button
        if (_certImageBytes != null)
           Center(
             child: ClipRRect(
               borderRadius: BorderRadius.circular(8),
               child: Image.memory(_certImageBytes!, height: 100, fit: BoxFit.cover)
             )
           ),
        const SizedBox(height: 10),
        Center(
          child: OutlinedButton.icon(
            onPressed: _pickCertificateImage,
            icon: const Icon(Icons.add_a_photo, color: Colors.blue),
            label: Text(_certImageBytes == null ? "Attach Product Photo (Required)" : "Change Photo"),
          ),
        ),
        const SizedBox(height: 15),

        Text("Product: ${_documentData!['product_name']}", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        const SizedBox(height: 10),
        const Text("Materials Used:", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
        Text("${_documentData!['material_used']}"),
        const SizedBox(height: 10),
        const Text("Cultural Origin / Style:", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
        Text("${_documentData!['cultural_origin']}", style: const TextStyle(color: Colors.blueAccent, fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        const Text("Creation Process:", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
        Text("${_documentData!['creation_process']}", style: const TextStyle(fontStyle: FontStyle.italic)),
        const SizedBox(height: 15),
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: Colors.green.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.green.shade200)),
          child: Row(
            children: const [
              Icon(Icons.verified, color: Colors.green),
              SizedBox(width: 8),
              Expanded(child: Text("Blockchain-Ready Digital Hash & QR Code will be attached in the PDF.", style: TextStyle(fontSize: 12, color: Colors.green))),
            ],
          ),
        )
      ],
    );
  }

  Widget _buildContractUI() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Center(child: Text("LEGAL AGREEMENT", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, letterSpacing: 1.2, color: Colors.purple))),
        const Divider(),
        Text("${_documentData!['title']}", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(8)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(" Party A: ${_documentData!['party_a']}", style: const TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text(" Party B: ${_documentData!['party_b']}", style: const TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
        ),
        const SizedBox(height: 10),
        const Text("Scope of Work:", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
        Text("${_documentData!['scope_of_work']}"),
        const SizedBox(height: 10),
        const Text("Payment Terms:", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
        Text("${_documentData!['payment_terms']}", style: const TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        const Text(" Risk Protection Clauses:", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.redAccent)),
        ...(_documentData!['risk_clauses'] as List).map((clause) => Padding(
          padding: const EdgeInsets.only(top: 4.0, left: 8.0),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("• ", style: TextStyle(fontWeight: FontWeight.bold)),
              Expanded(child: Text(clause.toString(), style: const TextStyle(fontStyle: FontStyle.italic))),
            ],
          ),
        )),
      ],
    );
  }

  Widget _buildInvoiceUI() {
    return Column(
      children: [
        const Text("INVOICE PREVIEW", style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
        const Divider(),
        Row(
          children: const [
            Expanded(flex: 3, child: Text("ITEM", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            Expanded(flex: 1, child: Text("QTY", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            Expanded(flex: 2, child: Text("PRICE", textAlign: TextAlign.right, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
          ],
        ),
        const Divider(),
        ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: (_documentData!['items'] as List).length,
          itemBuilder: (context, index) {
            var item = _documentData!['items'][index];
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4.0),
              child: Row(
                children: [
                  Expanded(flex: 3, child: Text(item['name'].toString(), style: const TextStyle(fontSize: 14))),
                  Expanded(flex: 1, child: Text("${item['qty']} ${item['unit']}", style: const TextStyle(fontSize: 12, color: Colors.grey))),
                  Expanded(flex: 2, child: Text("₹${item['total_amount']}", textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.bold))),
                ],
              ),
            );
          },
        ),
        const Divider(),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text("Grand Total", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text("₹${_documentData!['grand_total']}", style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.green)),
          ],
        )
      ],
    );
  }
}

// ==========================================
// TAB 2: VISION SCREEN 
// ==========================================
class VisionRepairScreen extends StatefulWidget {
  final String serverUrl;
  final String lang;
  const VisionRepairScreen({required this.serverUrl, required this.lang, super.key});

  @override
  State<VisionRepairScreen> createState() => _VisionRepairScreenState();
}

class _VisionRepairScreenState extends State<VisionRepairScreen> {
  XFile? _imageFile;
  Uint8List? _webImageBytes;
  bool _isLoading = false;
  Map<String, dynamic>? _diagnosisData;
  final AudioPlayer _audioPlayer = AudioPlayer();
  String? _generatedImageBase64;
  String _selectedMode = 'repair';
  
  final Map<String, String> _modes = {
    'repair': 'Machine Repair',
    'plant': 'Crop Disease',
    'quality': 'Quality Grade',
    'inventory': 'Stock Count',
    'pattern': 'Pattern Analysis',
    'modernize': 'Design Modernize',
    'market': 'Market Analysis',
  };

  Future<void> _pickImage(ImageSource source) async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: source, imageQuality: 50);
    if (image != null) {
      var f = await image.readAsBytes();
      setState(() { _imageFile = image; _webImageBytes = f; _diagnosisData = null; _generatedImageBase64 = null; });
    }
  }

  Future<void> _analyzeImage() async {
    if (_webImageBytes == null && _imageFile == null) return;
    setState(() { _isLoading = true; });

    try {
      var request = http.MultipartRequest('POST', Uri.parse('${widget.serverUrl}/diagnose'));
      request.headers['ngrok-skip-browser-warning'] = 'true';
      request.fields['language'] = widget.lang;
      request.fields['mode'] = _selectedMode; 

      if (kIsWeb) {
        request.files.add(http.MultipartFile.fromBytes('file', _webImageBytes!, filename: 'upload.jpg'));
      } else {
        request.files.add(await http.MultipartFile.fromPath('file', _imageFile!.path));
      }

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final jsonResp = json.decode(response.body);
        setState(() { 
            _diagnosisData = jsonResp['diagnosis_json']; 
            _isLoading = false; 
            if (_diagnosisData != null && _diagnosisData!.containsKey('generated_image_base64')) {
              _generatedImageBase64 = _diagnosisData!['generated_image_base64'];
            } else { _generatedImageBase64 = null; }
        });
        if (jsonResp['audio_base64'] != null) {
           await _audioPlayer.play(BytesSource(base64Decode(jsonResp['audio_base64'])));
        }
      } else {
        setState(() { _isLoading = false; });
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Server Error: ${response.statusCode}")));
      }
    } catch (e) {
      setState(() { _isLoading = false; });
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Connection Failed. Check Server URL.")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("KarigAI Vision ")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(color: Colors.white, border: Border.all(color: Colors.orange), borderRadius: BorderRadius.circular(8)),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: _selectedMode,
                  isExpanded: true,
                  icon: const Icon(Icons.category, color: Colors.orange),
                  items: _modes.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value, style: const TextStyle(fontWeight: FontWeight.bold)))).toList(),
                  onChanged: (val) => setState(() { _selectedMode = val!; _generatedImageBase64 = null; }),
                ),
              ),
            ),
            const SizedBox(height: 15),
            Container(
              height: 250, width: double.infinity,
              decoration: BoxDecoration(color: Colors.grey[200], borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade300)),
              child: _webImageBytes == null && _imageFile == null
                ? Column(mainAxisAlignment: MainAxisAlignment.center, children: const [Icon(Icons.add_a_photo, size: 50, color: Colors.grey), SizedBox(height: 10), Text("Select Photo to Analyze", style: TextStyle(color: Colors.grey))])
                : ClipRRect(borderRadius: BorderRadius.circular(12), child: kIsWeb && _webImageBytes != null ? Image.memory(_webImageBytes!, fit: BoxFit.contain) : Image.file(File(_imageFile!.path), fit: BoxFit.contain)),
            ),
            const SizedBox(height: 20),
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              ElevatedButton.icon(onPressed: () => _pickImage(ImageSource.camera), icon: const Icon(Icons.camera_alt), label: const Text("Camera")),
              const SizedBox(width: 10),
              ElevatedButton.icon(onPressed: () => _pickImage(ImageSource.gallery), icon: const Icon(Icons.photo_library), label: const Text("Gallery")),
            ]),
            const SizedBox(height: 15),
            if ((_imageFile != null || _webImageBytes != null) && !_isLoading)
              SizedBox(width: double.infinity, child: ElevatedButton(onPressed: _analyzeImage, style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade700, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 15)), child: Text("ANALYZE NOW (${_modes[_selectedMode]})"))),
            if (_isLoading) const Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator()),
            if (_diagnosisData != null)
              Container(
                margin: const EdgeInsets.only(top: 20), padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: Colors.green.shade50, borderRadius: BorderRadius.circular(10), border: Border.all(color: Colors.green)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Result: ${_diagnosisData!['appliance']}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const Divider(),
                    Text("Details: ${_diagnosisData!['error_code']}", style: const TextStyle(color: Colors.blueGrey, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    const Text("Solution / Advice:", style: TextStyle(fontWeight: FontWeight.bold)),
                    Text("${_diagnosisData!['solution']}"),
                    if (_generatedImageBase64 != null) ...[
                      const SizedBox(height: 15), const Divider(color: Colors.green), const SizedBox(height: 5),
                      const Text(" AI Modern Fusion Idea:", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.deepPurple)),
                      const SizedBox(height: 10),
                      ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(base64Decode(_generatedImageBase64!), width: double.infinity, fit: BoxFit.cover)),
                    ]
                  ],
                ),
              )
          ],
        ),
      ),
    );
  }
}



// ==========================================
// TAB 3: LEARNING SCREEN 
// ==========================================
class LearningScreen extends StatefulWidget {
  final String serverUrl;
  final String lang;
  final Function(String) onLangChange;

  const LearningScreen({required this.serverUrl, required this.lang, required this.onLangChange, super.key});

  @override
  State<LearningScreen> createState() => _LearningScreenState();
}

class _LearningScreenState extends State<LearningScreen> {
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  bool _isLoading = false;
  bool _isRecording = false;
  bool _wasLastQueryVoice = false; 
  
  late final AudioRecorder _audioRecorder;
  late final AudioPlayer _audioPlayer;

  XFile? _chatImageFile;
  Uint8List? _chatImageBytes;

  List<Map<String, dynamic>> _chatMessages = []; 

  // PROGRESS TRACKING & RECOMMENDATIONS VARIABLES
  int _userXP = 0;
  int _quizzesCompleted = 0;
  String _userLevel = "Lvl 1: Apprentice";

  final List<String> _recommendedPaths = [
    " Motor Pump Repair",
    " Safe Wiring 101",
    " Pipe Leakage Fix",
    " Measurement Basics"
  ];

  final Map<String, String> _languages = {
    'hi': 'Hindi (हिंदी)', 'en': 'English', 'bn': 'Bengali (বাংলা)', 
    'ta': 'Tamil (தமிழ்)', 'te': 'Telugu (తెలుగు)', 'mr': 'Marathi (मराठी)',
  };

  @override
  void initState() {
    super.initState();
    _audioRecorder = AudioRecorder();
    _audioPlayer = AudioPlayer();
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }


  Future<void> _playBase64Audio(String base64String) async {
    try {
      Uint8List audioBytes = base64Decode(base64String);
      await _audioPlayer.play(BytesSource(audioBytes)); 
    } catch (e) { print("Audio Error: $e"); }
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(_scrollController.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      final path = await _audioRecorder.stop();
      setState(() => _isRecording = false);
      if (path != null) _processVoiceQuery(path);
    } else {
      if (await _audioRecorder.hasPermission()) {
        await _audioRecorder.start(const RecordConfig(encoder: AudioEncoder.opus), path: '');
        setState(() => _isRecording = true);
      }
    }
  }

  Future<void> _processVoiceQuery(String path) async {
    setState(() => _isLoading = true);
    try {
      var request = http.MultipartRequest('POST', Uri.parse('${widget.serverUrl}/transcribe'));
      request.fields['language'] = widget.lang;
      request.fields['doc_type'] = 'auto'; 
      if (kIsWeb) {
        request.files.add(http.MultipartFile.fromBytes('file', await http.readBytes(Uri.parse(path)), filename: 'audio.webm'));
      } else {
        request.files.add(await http.MultipartFile.fromPath('file', path));
      }
      final response = await http.Response.fromStream(await request.send());
      if (response.statusCode == 200) {
        final jsonResp = json.decode(response.body);
        _searchController.text = jsonResp['transcribed_text'];
        _wasLastQueryVoice = true; 
        _searchKnowledge(); 
      } else {
        setState(() => _isLoading = false);
      }
    } catch(e) { setState(() => _isLoading = false); }
  }

  Future<void> _searchKnowledge() async {
    String query = _searchController.text.trim();
    if (query.isEmpty && _chatImageBytes == null) return; 
    
    _searchController.clear();
    FocusScope.of(context).unfocus();

    setState(() {
      _chatMessages.add({
        "isUser": true, 
        "text": query.isEmpty ? " Sent an Image" : query,
        "imageBytes": _chatImageBytes 
      });
      _isLoading = true;
    });
    _scrollToBottom();

    String contextStr = "";
    int startIndex = _chatMessages.length > 5 ? _chatMessages.length - 5 : 0;
    for (int i = startIndex; i < _chatMessages.length - 1; i++) {
      var msg = _chatMessages[i];
      if (msg["isUser"]) { contextStr += "User: ${msg['text']}\n"; } 
      else { contextStr += "AI: ${msg['data']['extracted_steps'].join(' ')}\n"; }
    }

    try {
      var request = http.MultipartRequest('POST', Uri.parse('${widget.serverUrl}/extract_knowledge'));
      request.fields['query'] = query;
      request.fields['language'] = widget.lang;
      request.fields['chat_history'] = contextStr; 
      request.fields['is_voice'] = _wasLastQueryVoice ? 'true' : 'false';

      if (_chatImageBytes != null) {
        if (kIsWeb) {
          request.files.add(http.MultipartFile.fromBytes('file', _chatImageBytes!, filename: 'upload.jpg'));
        } else {
          request.files.add(await http.MultipartFile.fromPath('file', _chatImageFile!.path));
        }
      }

      final response = await http.Response.fromStream(await request.send());

      if (response.statusCode == 200) {
        final jsonResp = json.decode(response.body);
        setState(() {
          _chatMessages.add({"isUser": false, "data": jsonResp['knowledge_data'], "source": jsonResp['source'] ?? "Cloud API"});
          _isLoading = false;
          _chatImageFile = null;
          _chatImageBytes = null; 
        });
        
        if (jsonResp['audio_base64'] != null) {
          _playBase64Audio(jsonResp['audio_base64']);
        }
        _wasLastQueryVoice = false; 
        _scrollToBottom();
      } else {
        setState(() { _isLoading = false; _chatImageFile = null; _chatImageBytes = null; });
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Server Error: ${response.statusCode}")));
      }
    } catch (e) {
      setState(() { _isLoading = false; _chatImageFile = null; _chatImageBytes = null; });
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Connection Failed.")));
    }
  }

  void _showImageSourceDialog() {
    showModalBottomSheet(
      context: context,
      builder: (BuildContext context) {
        return SafeArea(
          child: Wrap(
            children: <Widget>[
              ListTile(leading: const Icon(Icons.photo_library), title: const Text('Photo Library'), onTap: () { _pickChatImage(ImageSource.gallery); Navigator.of(context).pop(); }),
              ListTile(leading: const Icon(Icons.photo_camera), title: const Text('Camera'), onTap: () { _pickChatImage(ImageSource.camera); Navigator.of(context).pop(); }),
            ],
          ),
        );
      },
    );
  }

  Future<void> _pickChatImage(ImageSource source) async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: source, imageQuality: 50);
    if (image != null) {
      var f = await image.readAsBytes();
      setState(() { _chatImageFile = image; _chatImageBytes = f; });
    }
  }

  // Handle XP Updates when Quiz is answered
  void _handleQuizAnswer(int selectedIdx, int correctIdx) {
    if (selectedIdx == correctIdx) {
      setState(() {
        _userXP += 50;
        _quizzesCompleted += 1;
        if (_userXP >= 150) _userLevel = "Lvl 2: Journeyman";
        if (_userXP >= 300) _userLevel = "Lvl 3: Master Artisan";
      });
      
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("KarigAI Learning ")),
      body: Column(
        children: [
          // Language Selection
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(border: Border.all(color: Colors.orange), borderRadius: BorderRadius.circular(8)),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: widget.lang, isExpanded: true,
                  items: _languages.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
                  onChanged: (val) => widget.onLangChange(val!),
                ),
              ),
            ),
          ),
          
          //  DASHBOARD (Skill Gap & Recommendations)
          Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 4.0),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.blue.shade200)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(" $_userLevel", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue.shade900)),
                    Text(" $_userXP XP | $_quizzesCompleted Quizzes", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.orange.shade900)),
                  ],
                ),
                const SizedBox(height: 10),
                const Text("Suggested Learning Paths:", style: TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.bold)),
                const SizedBox(height: 5),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: _recommendedPaths.map((path) => Padding(
                      padding: const EdgeInsets.only(right: 8.0),
                      child: ActionChip(
                        label: Text(path, style: const TextStyle(fontSize: 12)),
                        backgroundColor: Colors.white,
                        side: BorderSide(color: Colors.blue.shade100),
                        onPressed: () {
                          _searchController.text = path;
                          _wasLastQueryVoice = false; 
                          _searchKnowledge();
                        }
                      ),
                    )).toList(),
                  ),
                )
              ],
            ),
          ),
          const Divider(),

          // Chat History
          Expanded(
            child: _chatMessages.isEmpty 
              ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: const [Icon(Icons.forum, size: 80, color: Colors.black12), SizedBox(height: 10), Text("Ask a question or upload a photo!", style: TextStyle(color: Colors.grey))]))
              : ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16.0),
                  itemCount: _chatMessages.length,
                  itemBuilder: (context, index) {
                    var msg = _chatMessages[index];
                    bool isUser = msg['isUser'];

                    if (isUser) {
                      return Align(
                        alignment: Alignment.centerRight,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 15, left: 50),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(color: Colors.orange.shade100, borderRadius: const BorderRadius.only(topLeft: Radius.circular(12), topRight: Radius.circular(12), bottomLeft: Radius.circular(12))),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              if (msg['imageBytes'] != null)
                                Padding(padding: const EdgeInsets.only(bottom: 8.0), child: ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(msg['imageBytes'], height: 120, fit: BoxFit.cover))),
                              Text(msg['text'], style: const TextStyle(fontSize: 15)),
                            ],
                          ),
                        ),
                      );
                    } else {
                      var data = msg['data'];
                      return Align(
                        alignment: Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 20, right: 20),
                          child: Card(
                            elevation: 2, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            child: Padding(
                              padding: const EdgeInsets.all(12.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(data['title'], style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.blue)),
                                  const SizedBox(height: 8),
                                  Wrap(spacing: 8.0, children: (data['tags'] as List).map((tag) => Chip(label: Text("#$tag", style: const TextStyle(fontSize: 10, color: Colors.blue)), backgroundColor: Colors.blue.shade50, visualDensity: VisualDensity.compact)).toList()),
                                  const Divider(),
                                  ...(data['extracted_steps'] as List).asMap().entries.map((entry) {
                                    return Padding(
                                      padding: const EdgeInsets.only(bottom: 6.0),
                                      child: Row(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          const Text("• ", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.orange)),
                                          Expanded(child: Text(entry.value, style: const TextStyle(fontSize: 14))),
                                        ],
                                      ),
                                    );
                                  }).toList(),
                                  
                                  if (data['quiz'] != null) ...[
                                    const SizedBox(height: 15),
                                    Container(
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(color: Colors.amber.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.amber.shade200)),
                                      child: StatefulBuilder(
                                        builder: (context, setQuizState) {
                                          int? selectedOption;
                                          bool isAnswered = msg.containsKey('selectedAnswer');
                                          if (isAnswered) selectedOption = msg['selectedAnswer'];
                                          
                                          int correctIndex = data['quiz']['correct_answer_index'];

                                          return Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                children: const [
                                                  Icon(Icons.quiz, color: Colors.amber, size: 18),
                                                  SizedBox(width: 5),
                                                  Text("Test Your Knowledge!", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.amber)),
                                                ],
                                              ),
                                              const SizedBox(height: 8),
                                              Text(data['quiz']['question'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                              const SizedBox(height: 10),
                                              ...(data['quiz']['options'] as List).asMap().entries.map((opt) {
                                                bool isCorrect = isAnswered && opt.key == correctIndex;
                                                bool isWrong = isAnswered && opt.key == selectedOption && selectedOption != correctIndex;
                                                
                                                Color btnColor = Colors.white;
                                                if (isCorrect) btnColor = Colors.green.shade100;
                                                if (isWrong) btnColor = Colors.red.shade100;

                                                return Padding(
                                                  padding: const EdgeInsets.only(bottom: 5.0),
                                                  child: InkWell(
                                                    onTap: isAnswered ? null : () {
                                                      setQuizState(() { msg['selectedAnswer'] = opt.key; });
                                                      // Call parent method to update XP
                                                      _handleQuizAnswer(opt.key, correctIndex);
                                                    },
                                                    child: Container(
                                                      width: double.infinity,
                                                      padding: const EdgeInsets.all(8),
                                                      decoration: BoxDecoration(color: btnColor, border: Border.all(color: isCorrect ? Colors.green : (isWrong ? Colors.red : Colors.grey.shade300)), borderRadius: BorderRadius.circular(6)),
                                                      child: Text(opt.value, style: TextStyle(fontSize: 12, color: isCorrect ? Colors.green.shade800 : (isWrong ? Colors.red.shade800 : Colors.black87))),
                                                    ),
                                                  ),
                                                );
                                              }).toList(),
                                              if (isAnswered)
                                                Padding(
                                                  padding: const EdgeInsets.only(top: 8.0),
                                                  child: Text(selectedOption == correctIndex ? "🎉 Sahi Jawab! (+50 XP)" : "❌ Galat Jawab. Sahi Jawab: ${data['quiz']['options'][correctIndex]}", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: selectedOption == correctIndex ? Colors.green : Colors.red)),
                                                )
                                            ],
                                          );
                                        }
                                      )
                                    )
                                  ],

                                  const SizedBox(height: 10),
                                 Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Row(
                                        children: [
                                          const Icon(Icons.verified, color: Colors.green, size: 14),
                                          const SizedBox(width: 4),
                                          Text("Trust Score: ${data['quality_score']}%", style: const TextStyle(color: Colors.green, fontSize: 10, fontWeight: FontWeight.bold)),
                                        ],
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: msg['source'] == "Edge Cache" ? Colors.purple.shade50 : Colors.blue.shade50,
                                          borderRadius: BorderRadius.circular(4),
                                          border: Border.all(color: msg['source'] == "Edge Cache" ? Colors.purple.shade200 : Colors.blue.shade200)
                                        ),
                                        child: Row(
                                          children: [
                                            Icon(msg['source'] == "Edge Cache" ? Icons.bolt : Icons.cloud_sync, size: 12, color: msg['source'] == "Edge Cache" ? Colors.purple : Colors.blue),
                                            const SizedBox(width: 4),
                                            Text(
                                              msg['source'] == "Edge Cache" ? "0ms Edge Cache" : "Cloud Inference", 
                                              style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: msg['source'] == "Edge Cache" ? Colors.purple : Colors.blue)
                                            ),
                                          ],
                                        ),
                                      )
                                    ],
                                  )
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    }
                  },
                ),
          ),
          
          if (_isLoading) const Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator()),

          if (_chatImageBytes != null)
            Container(
              color: Colors.grey.shade200, padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  Stack(
                    alignment: Alignment.topRight,
                    children: [
                      ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(_chatImageBytes!, height: 60, width: 60, fit: BoxFit.cover)),
                      GestureDetector(onTap: () => setState(() { _chatImageFile = null; _chatImageBytes = null; }), child: const CircleAvatar(radius: 10, backgroundColor: Colors.red, child: Icon(Icons.close, size: 12, color: Colors.white))),
                    ],
                  ),
                  const SizedBox(width: 10),
                  const Expanded(child: Text("Image ready to send. Ask a question or just hit send.", style: TextStyle(fontSize: 12, color: Colors.grey))),
                ],
              ),
            ),

          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
            decoration: BoxDecoration(color: Colors.white, boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 4, offset: const Offset(0, -2))]),
            child: Row(
              children: [
                GestureDetector(
                  onTap: _showImageSourceDialog,
                  child: CircleAvatar(backgroundColor: Colors.blue.shade100, child: Icon(Icons.add_a_photo, color: Colors.blue.shade800)),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: _toggleRecording,
                  child: CircleAvatar(backgroundColor: _isRecording ? Colors.red : Colors.orange.shade100, child: Icon(_isRecording ? Icons.stop : Icons.mic, color: _isRecording ? Colors.white : Colors.orange.shade800)),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    onChanged: (val) { if(_wasLastQueryVoice) _wasLastQueryVoice = false; },
                    decoration: InputDecoration(hintText: _isRecording ? "Listening..." : "Message Ustad...", border: OutlineInputBorder(borderRadius: BorderRadius.circular(25), borderSide: BorderSide.none), filled: true, fillColor: Colors.grey.shade100, contentPadding: const EdgeInsets.symmetric(horizontal: 15, vertical: 10)),
                    onSubmitted: (_) => _searchKnowledge(),
                  ),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: _isLoading ? null : _searchKnowledge,
                  child: CircleAvatar(backgroundColor: Colors.blue.shade700, child: const Icon(Icons.send, color: Colors.white, size: 20)),
                )
              ],
            ),
          ),
        ],
      ),
    );
  }
}










// ==========================================
// TAB 4: DOCUMENTS SCREEN 
// ==========================================
class DocumentsScreen extends StatefulWidget {
  final String serverUrl;
  final String lang;

  const DocumentsScreen({required this.serverUrl, required this.lang, super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  final TextEditingController _nameCtrl = TextEditingController(text: "Ramesh Kumar");
  final TextEditingController _ageCtrl = TextEditingController(text: "35");
  final TextEditingController _incomeCtrl = TextEditingController(text: "120000");
  
  String _selectedTrade = "Carpenter";
  String _selectedGender = "Male";
  String _selectedCategory = "OBC";

  bool _isLoading = false;
  List<dynamic>? _matchedSchemes;
  
  // Tracking & Status Updates Data
  List<Map<String, String>> _myApplications = [];

  final List<String> _trades = ["General Artisan", "Carpenter", "Tailor/Weaver", "Electrician", "Plumber", "Painter"];
  final List<String> _genders = ["Male", "Female", "Other"];
  final List<String> _categories = ["General", "OBC", "SC", "ST"];

  Future<void> _findSchemes() async {
    FocusScope.of(context).unfocus();
    setState(() { _isLoading = true; _matchedSchemes = null; });

    try {
      var request = http.MultipartRequest('POST', Uri.parse('${widget.serverUrl}/match_schemes'));
      request.fields['name'] = _nameCtrl.text;
      request.fields['trade'] = _selectedTrade;
      request.fields['age'] = _ageCtrl.text.isEmpty ? "30" : _ageCtrl.text;
      request.fields['gender'] = _selectedGender;
      request.fields['social_category'] = _selectedCategory;
      request.fields['income'] = _incomeCtrl.text.isEmpty ? "100000" : _incomeCtrl.text;

      final response = await http.Response.fromStream(await request.send());

      if (response.statusCode == 200) {
        final jsonResp = json.decode(response.body);
        setState(() {
          _matchedSchemes = jsonResp['schemes_data'];
          _matchedSchemes!.sort((a, b) => (b['match_score'] as int).compareTo(a['match_score'] as int));
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  // Auto-Fill Form Bottom Sheet
  Future<void> _openAutoFillForm(String schemeName) async {
    showDialog(context: context, builder: (ctx) => const Center(child: CircularProgressIndicator()));

    try {
      var request = http.MultipartRequest('POST', Uri.parse('${widget.serverUrl}/autofill_form'));
      request.fields['scheme_name'] = schemeName;
      request.fields['name'] = _nameCtrl.text;
      request.fields['trade'] = _selectedTrade;
      request.fields['age'] = _ageCtrl.text;
      request.fields['gender'] = _selectedGender;
      request.fields['social_category'] = _selectedCategory;
      request.fields['income'] = _incomeCtrl.text;

      final response = await http.Response.fromStream(await request.send());
      Navigator.pop(context); 

      if (response.statusCode == 200) {
        final data = json.decode(response.body)['form_data'];
        _showSmartFormSheet(data, schemeName);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error generating form.")));
      }
    } catch (e) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Connection Failed.")));
    }
  }

  void _showSmartFormSheet(Map<String, dynamic> formData, String schemeName) {
    List preFilled = formData['pre_filled_fields'];
    List missing = formData['missing_fields'];
    String trackingId = formData['tracking_id'];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom, left: 16, right: 16, top: 20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(" ${formData['form_title']}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.blue)),
              const SizedBox(height: 5),
              Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: Colors.green.shade50, borderRadius: BorderRadius.circular(8)), child: Row(children: const [Icon(Icons.check_circle, color: Colors.green, size: 16), SizedBox(width: 8), Text("Profile details auto-filled securely.", style: TextStyle(color: Colors.green, fontSize: 12))])),
              const SizedBox(height: 15),
              
              // Render Auto-filled locked fields
              ...preFilled.map((field) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(
                  readOnly: true,
                  decoration: InputDecoration(labelText: field['label'], border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)), filled: true, fillColor: Colors.grey.shade100, suffixIcon: const Icon(Icons.lock, color: Colors.grey, size: 16), isDense: true),
                  controller: TextEditingController(text: field['value']),
                ),
              )),
              
              const Divider(),
              const Text(" Action Required", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.orange)),
              const SizedBox(height: 10),

              // Render Missing Fields for user to type
              ...missing.map((field) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(decoration: InputDecoration(labelText: field['label'], border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)), isDense: true)),
              )),

              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity, height: 45,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pop(ctx);
                    setState(() {
                      _myApplications.add({"scheme": schemeName, "tracking_id": trackingId, "status": "Under Review", "date": "Just Now"});
                    });
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Application Submitted! Tracking ID: $trackingId"), backgroundColor: Colors.green));
                  },
                  icon: const Icon(Icons.send),
                  label: const Text("Submit Securely"),
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade700, foregroundColor: Colors.white),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      )
    );
  }

  // Submission Tracking UI
  void _showTrackingSheet() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text("My Applications (Tracking)", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Divider(),
            _myApplications.isEmpty
              ? const Center(child: Text("\n\nNo active applications.", style: TextStyle(color: Colors.grey)))
              : Expanded(
                  child: ListView.builder(
                    itemCount: _myApplications.length,
                    itemBuilder: (ctx, i) {
                      var app = _myApplications[i];
                      return ListTile(
                        leading: const CircleAvatar(backgroundColor: Colors.blue, child: Icon(Icons.description, color: Colors.white, size: 20)),
                        title: Text(app['scheme']!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                        subtitle: Text("Tracking: ${app['tracking_id']}\nSubmitted: ${app['date']}", style: const TextStyle(fontSize: 12)),
                        trailing: Chip(label: Text(app['status']!, style: const TextStyle(color: Colors.orange, fontSize: 10)), backgroundColor: Colors.orange.shade50),
                      );
                    },
                  ),
                )
          ],
        ),
      )
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("KarigAI Documents & Schemes ", style: TextStyle(fontSize: 18)),
        actions: [
          TextButton.icon(
            onPressed: _showTrackingSheet, 
            icon: const Icon(Icons.history, color: Colors.blue), 
            label: Text("Tracking (${_myApplications.length})", style: const TextStyle(color: Colors.blue, fontWeight: FontWeight.bold))
          )
        ],
      ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(12.0),
            decoration: BoxDecoration(color: Colors.white, boxShadow: [BoxShadow(color: Colors.grey.shade200, blurRadius: 4, offset: const Offset(0, 2))]),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(child: TextField(controller: _nameCtrl, decoration: const InputDecoration(labelText: "Full Name", isDense: true))),
                    const SizedBox(width: 8),
                    Expanded(child: TextField(controller: _ageCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: "Age", isDense: true))),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: DropdownButtonFormField<String>(value: _selectedGender, decoration: const InputDecoration(labelText: "Gender", isDense: true), items: _genders.map((g) => DropdownMenuItem(value: g, child: Text(g))).toList(), onChanged: (val) => setState(() => _selectedGender = val!))),
                    const SizedBox(width: 8),
                    Expanded(child: DropdownButtonFormField<String>(value: _selectedCategory, decoration: const InputDecoration(labelText: "Category", isDense: true), items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(), onChanged: (val) => setState(() => _selectedCategory = val!))),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(flex: 2, child: DropdownButtonFormField<String>(value: _selectedTrade, decoration: const InputDecoration(labelText: "Trade", isDense: true), items: _trades.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(), onChanged: (val) => setState(() => _selectedTrade = val!))),
                    const SizedBox(width: 8),
                    Expanded(flex: 1, child: TextField(controller: _incomeCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: "Income (₹)", isDense: true))),
                  ],
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : _findSchemes,
                    icon: _isLoading ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Icon(Icons.search),
                    label: const Text("Find Eligible Schemes"),
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade700, foregroundColor: Colors.white),
                  ),
                )
              ],
            ),
          ),

          Expanded(
            child: _isLoading
                ? const Center(child: Text("Fetching real-time schemes from AI..."))
                : _matchedSchemes == null
                    ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: const [Icon(Icons.assignment_ind, size: 60, color: Colors.black12), SizedBox(height: 10), Text("Enter details to check eligibility.", style: TextStyle(color: Colors.grey))]))
                    : ListView.builder(
                        padding: const EdgeInsets.all(12.0),
                        itemCount: _matchedSchemes!.length,
                        itemBuilder: (context, index) {
                          var scheme = _matchedSchemes![index];
                          int score = scheme['match_score'] ?? 0;
                          Color scoreColor = score >= 80 ? Colors.green : (score >= 50 ? Colors.orange : Colors.red);

                          return Card(
                            elevation: 3, margin: const EdgeInsets.only(bottom: 15),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            child: Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Expanded(child: Text(scheme['name'], style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.blue.shade900))),
                                      Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5), decoration: BoxDecoration(color: scoreColor.withOpacity(0.1), borderRadius: BorderRadius.circular(20), border: Border.all(color: scoreColor)), child: Text("$score% Match", style: TextStyle(color: scoreColor, fontWeight: FontWeight.bold, fontSize: 12)))
                                    ],
                                  ),
                                  const SizedBox(height: 5),
                                  Text(scheme['description'], style: const TextStyle(fontSize: 12, color: Colors.black87)),
                                  const SizedBox(height: 5),
                                  Row(children: [const Icon(Icons.check_circle, color: Colors.green, size: 14), const SizedBox(width: 6), Expanded(child: Text(scheme['eligibility_reason'], style: const TextStyle(fontSize: 12, color: Colors.green)))]),
                                  
                                  // Auto-Fill Trigger Button
                                  const SizedBox(height: 15),
                                  SizedBox(
                                    width: double.infinity,
                                    child: OutlinedButton.icon(
                                      onPressed: () => _openAutoFillForm(scheme['name']),
                                      icon: const Icon(Icons.bolt, color: Colors.orange),
                                      label: const Text("Apply with KarigAI (Auto-Fill)"),
                                      style: OutlinedButton.styleFrom(foregroundColor: Colors.blue.shade800, side: BorderSide(color: Colors.blue.shade200)),
                                    ),
                                  )
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}