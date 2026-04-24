"""
Simple pattern-based decision maker (baseline for comparison)
Fast but less intelligent than Cohere-based system
"""

class SimplePatternMatcher:
    """
    Baseline decision maker using keyword matching.
    No AI, just simple rules - FAST but less accurate.
    """
    
    def __init__(self):
        # Define keyword patterns for each intent
        self.automation_keywords = {
            'open': ['open', 'launch', 'start', 'run'],
            'close': ['close', 'quit', 'exit app', 'shutdown', 'kill'],
            'play': ['play', 'watch', 'listen'],
            'system': ['mute', 'unmute', 'volume', 'lock', 'sleep'],
            'content': ['write', 'create document', 'generate text', 'compose', 'draft'],
            'google_search': ['google', 'search google', 'look up'],
            'youtube_search': ['youtube search', 'search youtube', 'find on youtube']
        }
        
        self.realtime_keywords = [
            'who is', 'what is', 'where is', 'when is',
            'current', 'latest', 'recent', 'today',
            'weather', 'news', 'president', 'prime minister',
            'price', 'stock', 'score', 'result',
            'happening', 'update', 'status', 'now',
            'tell me about', 'information about'
        ]
        
        self.image_keywords = [
            'generate image', 'create image', 'make image',
            'draw', 'picture of', 'image of'
        ]
        
        self.exit_keywords = ['bye', 'goodbye', 'exit', 'quit', 'see you']
        
    def decide(self, query: str) -> list:
        """
        Classify query using simple pattern matching.
        
        Args:
            query: User's input text
            
        Returns:
            List of decisions (e.g., ['general how are you?'])
        """
        query_lower = query.lower().strip()
        decisions = []
        
        # Check for exit
        if any(keyword in query_lower for keyword in self.exit_keywords):
            decisions.append('exit')
            return decisions
        
        # Check for image generation
        if any(keyword in query_lower for keyword in self.image_keywords):
            # Extract prompt after the trigger keyword
            for keyword in self.image_keywords:
                if keyword in query_lower:
                    prompt = query_lower.split(keyword)[-1].strip()
                    if prompt:
                        decisions.append(f"generate image {prompt}")
                    break
        
        # Check for automation tasks
        automation_found = False
        
        # Check for 'open' command
        if any(keyword in query_lower for keyword in self.automation_keywords['open']):
            parts = query_lower.split('open')
            if len(parts) > 1:
                targets = parts[1].strip()
                # Handle multiple targets: "open chrome and facebook"
                targets = targets.replace(' and ', ',').split(',')
                for target in targets:
                    target = target.strip()
                    if target and target not in ['it', 'that', 'this', '']:
                        decisions.append(f"open {target}")
                        automation_found = True
        
        # Check for 'close' command
        if any(keyword in query_lower for keyword in self.automation_keywords['close']):
            parts = query_lower.split('close')
            if len(parts) > 1:
                targets = parts[1].strip()
                targets = targets.replace(' and ', ',').split(',')
                for target in targets:
                    target = target.strip()
                    if target and target not in ['it', 'that', 'this', '']:
                        decisions.append(f"close {target}")
                        automation_found = True
        
        # Check for 'play' command
        if any(keyword in query_lower for keyword in self.automation_keywords['play']):
            parts = query_lower.split('play')
            if len(parts) > 1:
                song = parts[1].strip()
                if song:
                    decisions.append(f"play {song}")
                    automation_found = True
        
        # Check for system commands
        for keyword in self.automation_keywords['system']:
            if keyword in query_lower:
                decisions.append(f"system {keyword}")
                automation_found = True
                break
        
        # Check for content writing
        for keyword in ['write', 'create document', 'compose', 'draft']:
            if keyword in query_lower:
                parts = query_lower.split(keyword)
                if len(parts) > 1:
                    topic = parts[1].strip()
                    if topic:
                        decisions.append(f"content {topic}")
                        automation_found = True
                break
        
        # Check for Google search
        for keyword in ['google', 'search google']:
            if keyword in query_lower:
                parts = query_lower.split(keyword)
                if len(parts) > 1:
                    search_query = parts[1].strip()
                    if search_query:
                        decisions.append(f"google search {search_query}")
                        automation_found = True
                break
        
        # Check for YouTube search
        for keyword in ['youtube search', 'search youtube']:
            if keyword in query_lower:
                parts = query_lower.split(keyword)
                if len(parts) > 1:
                    search_query = parts[1].strip()
                    if search_query:
                        decisions.append(f"youtube search {search_query}")
                        automation_found = True
                break
        
        # Check for realtime queries
        is_realtime = any(keyword in query_lower for keyword in self.realtime_keywords)
        
        # If no automation tasks detected, classify as general or realtime
        if not automation_found and not decisions:
            if is_realtime:
                decisions.append(f"realtime {query}")
            else:
                decisions.append(f"general {query}")
        elif automation_found and is_realtime:
            # If both automation and realtime detected, add realtime too
            decisions.append(f"realtime {query}")
        
        # If still no decisions, default to general
        if not decisions:
            decisions.append(f"general {query}")
        
        return decisions


# Test function
if __name__ == "__main__":
    matcher = SimplePatternMatcher()
    
    # Test cases
    test_queries = [
        "How are you?",
        "Who is the president?",
        "Open Chrome and Facebook",
        "Play Despacito",
        "What is the weather today?",
        "Generate image of a sunset",
        "Close notepad",
        "Tell me a joke",
        "Write an application for leave",
        "Search google for python tutorials",
        "Open telegram and instagram",
        "Bye"
    ]
    
    print("🧪 Testing Simple Pattern Matcher:\n")
    for query in test_queries:
        result = matcher.decide(query)
        print(f"Query: '{query}'")
        print(f"Decision: {result}\n")