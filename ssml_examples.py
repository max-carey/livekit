"""
SSML (Speech Synthesis Markup Language) Examples for LiveKit Agent

This file contains examples of how to use SSML tags to customize pronunciation,
emphasis, and speech characteristics in your LiveKit agent.
"""

import re
from typing import AsyncIterable


class SSMLExamples:
    """
    Collection of SSML techniques for customizing speech in LiveKit agents.
    """
    
    @staticmethod
    def add_emphasis_examples():
        """
        Examples of different emphasis levels and techniques.
        """
        examples = {
            "strong_emphasis": "<emphasis level='strong'>to put on</emphasis>",
            "moderate_emphasis": "<emphasis level='moderate'>phrasal verb</emphasis>",
            "reduced_emphasis": "<emphasis level='reduced'>background information</emphasis>",
            "prosody_emphasis": "<prosody rate='slow' pitch='high'>important point</prosody>",
        }
        return examples
    
    @staticmethod
    def add_pronunciation_examples():
        """
        Examples of custom pronunciation for technical terms and abbreviations.
        """
        pronunciations = {
            "API": "<say-as interpret-as='spell-out'>API</say-as>",
            "REST": "<phoneme alphabet='ipa' ph='rɛst'>REST</phoneme>",
            "SQL": "<say-as interpret-as='characters'>SQL</say-as>",
            "kubectl": "<phoneme alphabet='ipa' ph='kubəkəntrəl'>kubectl</phoneme>",
            "AWS": "<say-as interpret-as='spell-out'>AWS</say-as>",
            "UI": "<say-as interpret-as='spell-out'>UI</say-as>",
            "URL": "<say-as interpret-as='spell-out'>URL</say-as>",
            "npm": "<say-as interpret-as='spell-out'>npm</say-as>",
            "LiveKit": "<phoneme alphabet='ipa' ph='laɪv kɪt'>LiveKit</phoneme>",
            "async": "<phoneme alphabet='ipa' ph='eɪsɪŋk'>async</phoneme>",
            "nginx": "<phoneme alphabet='ipa' ph='ɛndʒɪn ɛks'>nginx</phoneme>",
        }
        return pronunciations
    
    @staticmethod
    def add_pause_examples():
        """
        Examples of different pause durations and types.
        """
        pauses = {
            "short_pause": "<break time='200ms'/>",
            "medium_pause": "<break time='500ms'/>",
            "long_pause": "<break time='1s'/>",
            "sentence_pause": "<break strength='medium'/>",
            "paragraph_pause": "<break strength='strong'/>",
        }
        return pauses
    
    @staticmethod
    def add_prosody_examples():
        """
        Examples of prosody (rate, pitch, volume) modifications.
        """
        prosody_examples = {
            "slow_clear": "<prosody rate='slow'>speaking slowly and clearly</prosody>",
            "fast_excited": "<prosody rate='fast' pitch='high'>speaking quickly with excitement</prosody>",
            "whisper": "<prosody volume='soft'>speaking quietly</prosody>",
            "loud_important": "<prosody volume='loud'>speaking loudly for emphasis</prosody>",
            "low_pitch": "<prosody pitch='low'>speaking with a deep voice</prosody>",
            "high_pitch": "<prosody pitch='high'>speaking with a high voice</prosody>",
        }
        return prosody_examples


def create_ssml_formatter():
    """
    Creates a function that applies SSML formatting to text.
    """
    
    # Pronunciation dictionary
    pronunciations = SSMLExamples.add_pronunciation_examples()
    
    # Emphasis patterns
    emphasis_patterns = [
        (r'\bto put on\b', '<emphasis level="strong">to put on</emphasis>'),
        (r'\bput on\b', '<emphasis level="moderate">put on</emphasis>'),
        (r'\bphrasal verb\b', '<emphasis level="moderate">phrasal verb</emphasis>'),
        (r'\bimportant\b', '<emphasis level="strong">important</emphasis>'),
        (r'\bkey\b', '<emphasis level="moderate">key</emphasis>'),
    ]
    
    def format_text_with_ssml(text: str) -> str:
        """
        Applies SSML formatting to text for better pronunciation and emphasis.
        """
        modified_text = text
        
        # Apply pronunciation rules
        for term, pronunciation in pronunciations.items():
            modified_text = re.sub(
                rf'\b{term}\b',
                pronunciation,
                modified_text,
                flags=re.IGNORECASE
            )
        
        # Apply emphasis patterns
        for pattern, replacement in emphasis_patterns:
            modified_text = re.sub(
                pattern,
                replacement,
                modified_text,
                flags=re.IGNORECASE
            )
        
        # Add pauses after sentences
        modified_text = re.sub(
            r'([.!?])\s+',
            r'\1 <break time="500ms"/> ',
            modified_text
        )
        
        # Add pauses after commas
        modified_text = re.sub(
            r'([,])\s+',
            r'\1 <break time="200ms"/> ',
            modified_text
        )
        
        # Wrap in SSML speak tags if not already wrapped
        if not modified_text.strip().startswith('<speak>'):
            modified_text = f'<speak>{modified_text}</speak>'
        
        return modified_text
    
    return format_text_with_ssml


# Example usage in an agent
async def example_agent_tts_node(
    self,
    text: AsyncIterable[str],
    model_settings
) -> AsyncIterable:
    """
    Example of how to integrate SSML formatting in an agent's tts_node.
    """
    formatter = create_ssml_formatter()
    
    async def apply_ssml_formatting(input_text: AsyncIterable[str]) -> AsyncIterable[str]:
        async for chunk in input_text:
            formatted_chunk = formatter(chunk)
            yield formatted_chunk
    
    # Process with SSML formatting through base TTS implementation
    async for frame in await super().tts_node(
        apply_ssml_formatting(text),
        model_settings
    ):
        yield frame


# Example SSML templates for common scenarios
SSML_TEMPLATES = {
    "greeting": """
    <speak>
        <prosody rate="slow" pitch="medium">Hello there!</prosody>
        <break time="300ms"/>
        How can I help you today?
    </speak>
    """,
    
    "emphasis_question": """
    <speak>
        Do you know what the <emphasis level="strong">phrasal verb</emphasis> 
        <emphasis level="strong">to put on</emphasis> means?
        <break time="500ms"/>
        It's a very <emphasis level="moderate">common expression</emphasis> in English.
    </speak>
    """,
    
    "technical_explanation": """
    <speak>
        Let me explain the <say-as interpret-as="spell-out">API</say-as> concept.
        <break time="300ms"/>
        <prosody rate="slow">An API, or Application Programming Interface,</prosody>
        <break time="200ms"/>
        is a set of rules that allows different software applications to communicate.
    </speak>
    """,
    
    "list_with_pauses": """
    <speak>
        Here are the key points:
        <break time="500ms"/>
        <prosody rate="slow">
            First, <emphasis level="moderate">understanding the basics</emphasis>
            <break time="300ms"/>
            Second, <emphasis level="moderate">practicing regularly</emphasis>
            <break time="300ms"/>
            And finally, <emphasis level="strong">applying what you learn</emphasis>
        </prosody>
    </speak>
    """
}


if __name__ == "__main__":
    # Example usage
    formatter = create_ssml_formatter()
    
    test_text = "Do you know what the phrasal verb to put on means? It's commonly used in English."
    formatted = formatter(test_text)
    print("Original:", test_text)
    print("Formatted:", formatted) 