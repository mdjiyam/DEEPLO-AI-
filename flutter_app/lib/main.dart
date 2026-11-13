import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

// Backend-এর ঠিকানা build-এর সময় GitHub Actions থেকে আসে (BACKEND_URL)।
// নিজের কম্পিউটারে টেস্ট করলে: flutter run --dart-define=BACKEND_URL=http://localhost:8000
const String backendUrl = String.fromEnvironment(
  'BACKEND_URL',
  defaultValue: 'http://localhost:8000',
);

void main() => runApp(const ChatApp());

class ChatApp extends StatelessWidget {
  const ChatApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Chat',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatMessage {
  final String role; // 'user' বা 'assistant'
  String content;
  ChatMessage(this.role, this.content);

  Map<String, String> toJson() => {'role': role, 'content': content};
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scroll = ScrollController();
  bool _sending = false;

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 150),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) return;

    _controller.clear();
    setState(() {
      _messages.add(ChatMessage('user', text));
      _messages.add(ChatMessage('assistant', ''));
      _sending = true;
    });
    _scrollToBottom();

    final reply = _messages.last;
    // শেষের খালি assistant message বাদে পুরো history পাঠানো হয়
    final history =
        _messages.sublist(0, _messages.length - 1).map((m) => m.toJson()).toList();

    final client = http.Client();
    try {
      final request = http.Request('POST', Uri.parse('$backendUrl/chat'))
        ..headers['Content-Type'] = 'application/json'
        ..body = jsonEncode({'messages': history});

      final response = await client.send(request);

      if (response.statusCode != 200) {
        setState(() => reply.content = 'সমস্যা হয়েছে (${response.statusCode})');
      } else {
        await for (final chunk in response.stream.transform(utf8.decoder)) {
          setState(() => reply.content += chunk);
          _scrollToBottom();
        }
      }
    } catch (e) {
      setState(() => reply.content = 'Server-এর সাথে যোগাযোগ করা যায়নি: $e');
    } finally {
      client.close();
      setState(() => _sending = false);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('AI Chat')),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? const Center(child: Text('কিছু জিজ্ঞেস করুন...'))
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length,
                    itemBuilder: (context, i) {
                      final m = _messages[i];
                      final isUser = m.role == 'user';
                      return Align(
                        alignment:
                            isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 4),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 10),
                          constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.8,
                          ),
                          decoration: BoxDecoration(
                            color: isUser
                                ? scheme.primaryContainer
                                : scheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: SelectableText(
                            m.content.isEmpty ? '...' : m.content,
                          ),
                        ),
                      );
                    },
                  ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 5,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(),
                      decoration: InputDecoration(
                        hintText: 'মেসেজ লিখুন...',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _sending ? null : _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
