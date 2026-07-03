"""
Simple pattern-based decision maker (baseline for comparison)
Fast but less intelligent than Cohere-based system
"""

import re


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

        self.reminder_keywords = [
            'remind me', 'set a reminder', 'reminder'
        ]

        self.exit_keywords = ['bye', 'goodbye', 'exit', 'quit', 'see you']

    def _youtube_control_action(self, query_lower: str) -> str | None:
        """
        Return the YouTube controller action for obvious media-control commands.
        Kept conservative so generic system commands like "mute my laptop" still
        stay with the system automation path.
        """
        query_norm = " ".join(query_lower.replace("-", " ").split())
        has_video_context = any(
            keyword in query_norm
            for keyword in ["youtube", "video", "captions", "caption", "subtitle"]
        )

        if any(phrase in query_norm for phrase in ["close youtube", "quit youtube", "exit youtube"]):
            return "close youtube"

        if any(phrase in query_norm for phrase in ["what is playing", "what's playing", "current video", "youtube status"]):
            return "status"

        if "sleep timer" in query_norm or "pause after" in query_norm or "stop after" in query_norm:
            match = re.search(r"\d+(?:\.\d+)?", query_norm)
            return f"sleep timer {match.group(0)}" if match else "sleep timer"

        if any(phrase in query_norm for phrase in [
            "cancel timer", "cancel the timer",
            "stop timer", "stop the timer",
            "clear timer", "clear the timer",
            "remove timer", "remove the timer",
        ]):
            return "cancel timer"

        if "skip forward" in query_norm or "fast forward" in query_norm:
            match = re.search(r"\d+", query_norm)
            return f"skip forward {match.group(0)}" if match else "skip forward"

        if "skip back" in query_norm or "skip backward" in query_norm or "rewind" in query_norm:
            match = re.search(r"\d+", query_norm)
            return f"skip backward {match.group(0)}" if match else "skip backward"

        if any(phrase in query_norm for phrase in ["next video", "next song", "next track", "skip video"]):
            return "next video"

        if any(phrase in query_norm for phrase in ["previous video", "previous song", "previous track"]):
            return "previous"

        if any(phrase in query_norm for phrase in ["start over", "restart video", "replay video"]):
            return "previous"

        if any(phrase in query_norm for phrase in ["normal speed", "slow down", "speed up", "playback rate"]):
            if "normal speed" in query_norm:
                return "normal speed"
            if "slow down" in query_norm:
                return "slow down"
            if "speed up" in query_norm:
                return "speed up"
            match = re.search(r"\d+(?:\.\d+)?", query_norm)
            return f"speed {match.group(0)}" if match else "speed"

        if "speed" in query_norm and (has_video_context or re.search(r"\bspeed\s+(?:to\s+)?\d", query_norm)):
            match = re.search(r"\d+(?:\.\d+)?", query_norm)
            return f"speed {match.group(0)}" if match else "speed"

        if any(phrase in query_norm for phrase in ["fullscreen", "full screen", "exit full"]):
            return "fullscreen"

        if any(word in query_norm for word in ["captions", "caption", "subtitle", "subtitles", "cc"]):
            return "captions"

        if any(phrase in query_norm for phrase in ["theater mode", "theatre mode", "cinema mode"]):
            return "theater"

        if "ambient" in query_norm:
            return "ambient"

        if "autoplay" in query_norm or "auto play" in query_norm:
            return "autoplay"

        if "volume" in query_norm and has_video_context:
            match = re.search(r"\d+", query_norm)
            if match:
                return f"volume {match.group(0)}"
            if any(word in query_norm for word in ["up", "louder", "increase"]):
                return "volume up"
            if any(word in query_norm for word in ["down", "quieter", "decrease", "lower"]):
                return "volume down"
            return "volume"

        if any(word in query_norm for word in ["mute", "unmute", "silence"]) and has_video_context:
            return "mute" if "unmute" not in query_norm else "unmute"

        if any(phrase in query_norm for phrase in ["pause the video", "pause video", "stop the video", "stop video"]):
            return "pause"

        if any(phrase in query_norm for phrase in ["resume the video", "resume video", "continue the video", "unpause", "start video"]):
            return "resume"

        if has_video_context and re.search(r"\b(pause|stop)\b", query_norm):
            return "pause"

        if has_video_context and re.search(r"\b(resume|continue|unpause)\b", query_norm):
            return "resume"

        if has_video_context and query_norm in {"pause", "resume", "fullscreen", "mute", "unmute"}:
            return query_norm

        return None

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

        youtube_action = self._youtube_control_action(query_lower)
        if youtube_action:
            return [f"youtube control {youtube_action}"]

        # Check for exit
        if any(keyword in query_lower for keyword in self.exit_keywords):
            decisions.append('exit')
            return decisions

        automation_found = False
        
        # Check for image generation
        if any(keyword in query_lower for keyword in self.image_keywords):
            # Extract prompt after the trigger keyword
            for keyword in self.image_keywords:
                if keyword in query_lower:
                    prompt = query_lower.split(keyword)[-1].strip()
                    if prompt:
                        decisions.append(f"generate image {prompt}")
                    break

        # Check for reminders
        for keyword in self.reminder_keywords:
            if keyword in query_lower:
                payload = query_lower.split(keyword, 1)[-1].strip()
                if payload:
                    decisions.append(f"reminder {payload}")
                    automation_found = True
                break
        
        # Check for automation tasks
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
