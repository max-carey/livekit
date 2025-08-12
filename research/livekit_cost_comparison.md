# Cost-Effective LiveKit Voice AI Providers

Building a bilingual voice agent with LiveKit Agents involves choosing a Speech-to-Text (STT) engine, a Text-to-Speech (TTS) engine, and a Large Language Model (LLM) that all support **Mexican Spanish (es-MX)** and **U.S. English (en-US)**. The goal is to minimize costs (even if using low-cost paid tiers) while maintaining reasonable quality. Below we compare compatible providers in each category (as listed in LiveKit’s docs) on pricing and multilingual support, then recommend an optimal combination.

## STT (Speech-to-Text) Providers Comparison

LiveKit Agents supports many STT services (Deepgram, OpenAI Whisper, AssemblyAI, Amazon Transcribe, etc.), all of which offer **multilingual transcription**. Key factors are cost per minute of audio and quality for Spanish/English speech.

| **STT Provider**         | **Pricing**               | **Language Support**          | **Notes** |
|--------------------------|---------------------------|--------------------------------|-----------|
| **OpenAI Whisper API**   | $0.006 per minute | 100+ languages (Spanish, English, etc.) | High accuracy open-source model; very affordable pay-as-you-go pricing. |
| **Deepgram Nova**        | ~$0.0043 per minute (at volume) | 30+ languages (incl. es & en) | Real-time streaming; supports Spanish (Nova-2 added es-MX). Extremely low cost at scale. |
| **AssemblyAI**           | $0.015 per minute | English (Spanish in beta) | Higher cost (~2× Whisper). Extra features like summarization and webhooks. |
| **Amazon Transcribe**    | $0.024/min (first 250k min) | ~30 languages (es-MX, en-US) | Tiered volume discounts (down to $0.0102/min at scale). |
| *Local Whisper model*    | Free (self-hosted) | Multilingual (es & en) | Requires infrastructure; no API cost. |

**Analysis:** OpenAI’s Whisper API and Deepgram’s Nova are the most cost-effective. Whisper’s flat $0.006/min rate is very cheap and accurate for both English and Spanish. Deepgram Nova-2 is slightly cheaper at scale (~$0.0043/min) and supports es-MX.

## TTS (Text-to-Speech) Providers Comparison

For TTS, we need lifelike voice synthesis in both **Mexican Spanish** and **US English**.

| **TTS Provider**       | **Pricing** | **Spanish & English Voices** | **Notes** |
|------------------------|-------------|------------------------------|-----------|
| **Amazon Polly (Neural)** | $16 per 1M characters (~$0.000016/char) | Yes – e.g. *Mia* (es-MX), *Andrés* (es-MX), many en-US voices | Cost-effective. Standard voices even cheaper ($4 per 1M). Supports SSML. |
| **Google Cloud TTS (WaveNet)** | $16 per 1M chars (~$0.000016/char) | Yes – includes es-MX and en-US voices | Similar pricing to Polly. High-quality WaveNet voices. |
| **Cartesia Sonic**     | ~$2.40 per hour of speech (~$33 per 1M chars) | Yes – Latin American Spanish & English voices | Ultra-low latency (sub-50ms). More expensive than AWS/Google. |
| **ElevenLabs**         | ~$0.18–$0.30 per 1K chars (~$180–$300 per 1M) | Yes – 70+ languages | Very high quality but much higher cost. |
| **Azure Cognitive TTS**| ~$16 per 1M chars | Yes – supports es-MX, en-US | Comparable neural voice quality and pricing. |

**Analysis:** Amazon Polly, Google TTS, and Azure offer high-quality neural voices in both languages at ~\$15–\$16 per million characters. For lowest cost with good quality, **Amazon Polly Neural** is recommended.

## LLM Providers Comparison

| **LLM Provider** | **Model Example** | **Pricing (per 1K tokens)** | **Multilingual Support** | **Notes** |
|------------------|-------------------|-----------------------------|--------------------------|-----------|
| **OpenAI**       | GPT-3.5 Turbo     | $0.002 | Excellent | Most cost-effective. Fluent in es & en. |
| **Anthropic**    | Claude Instant    | ~$0.0024 output / $0.80 per 1M input | Very good | Large context window. Slightly higher cost. |
| **Azure OpenAI** | GPT-3.5 Turbo     | ~$0.002 | Excellent | Same as OpenAI; Azure hosting. |
| **Together AI / Ollama** | Llama-2 13B | Varies | Good | Open-source; no API fee but requires hosting. |

**Analysis:** **OpenAI GPT-3.5 Turbo** is the best balance of cost and quality at $0.002 per 1K tokens.

## Recommended Low-Cost Provider Combination

- **STT:** OpenAI Whisper API – $0.006/minute, accurate for es-MX & en-US.
- **TTS:** Amazon Polly Neural – $16 per 1M chars, locale-specific voices for es-MX & en-US.
- **LLM:** OpenAI GPT-3.5 Turbo – $0.002 per 1K tokens, excellent bilingual capability.

**Example Cost Estimate:**  
1 min transcription = $0.006  
100-char TTS output = ~$0.0016  
1000-token LLM output = $0.002  
→ An hour of bilingual conversation could cost just a few cents.

## Sources

1. LiveKit Docs – Supported STT, TTS, LLM integrations.
2. OpenAI – Whisper API pricing, GPT-3.5 Turbo pricing.
3. Deepgram – Nova-2 multilingual support and pricing.
4. AWS – Amazon Polly pricing and es-MX voices.
5. Google Cloud – TTS pricing.
6. Cartesia AI – Sonic TTS pricing.
7. ElevenLabs – API rates.
8. Anthropic – Claude Instant pricing.
