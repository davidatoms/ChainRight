import math
import zlib
import json
from typing import Dict, Any, List

class LLMGeometrics:
    """
    Implements relativistic metrics for LLM interactions to determine 
    computational difficulty (Effort) for the blockchain.
    """
    
    @staticmethod
    def calculate_entropy(text: str) -> float:
        """
        Calculates Shannon Entropy of a string.
        High entropy = High complexity/Information density.
        """
        if not text:
            return 0.0
        
        # Calculate frequency of each character
        probs = [text.count(c) / len(text) for c in set(text)]
        entropy = -sum(p * math.log2(p) for p in probs)
        return entropy

    @staticmethod
    def calculate_energy(text: str) -> float:
        """
        Calculates Information Energy (E) using zlib compression ratio.
        Higher ratio = Less repetitive = More information 'Energy'.
        """
        if not text:
            return 0.0
        
        encoded = text.encode('utf-8')
        compressed = zlib.compress(encoded)
        
        # Ratio of compressed to original (0.0 to 1.0+)
        # We invert it so high density = high energy
        ratio = len(compressed) / max(len(encoded), 1)
        return ratio

    @staticmethod
    def calculate_curvature(input_text: str, output_text: str) -> float:
        """
        Calculates Semantic Curvature (kappa) between prompt and response.
        Measures the 'turn' in information space using character distribution shift.
        """
        if not input_text or not output_text:
            return 1.0 # Default curvature
            
        def get_dist(t):
            chars = set(t.lower())
            return {c: t.lower().count(c) / len(t) for c in chars}
            
        dist1 = get_dist(input_text)
        dist2 = get_dist(output_text)
        
        # Calculate Hellinger-like distance between distributions
        all_chars = set(dist1.keys()) | set(dist2.keys())
        distance = 0.0
        for c in all_chars:
            p = dist1.get(c, 0.0)
            q = dist2.get(c, 0.0)
            distance += (math.sqrt(p) - math.sqrt(q)) ** 2
            
        kappa = math.sqrt(distance / 2.0)
        # Scale curvature: Higher distance = sharper turn
        return max(kappa, 0.1)

    @staticmethod
    def calculate_gaussian_well(text: str) -> float:
        """
        Calculates 'Well Depth' (Stability).
        A Gaussian well is formed when the information mass is highly 
        concentrated on a stable attractor (repetitive or structured).
        
        Depth = 1.0 (Deep Well/Stable) to 0.0 (Chaotic).
        """
        if not text:
            return 0.0
        
        # We use compression ratio as stability proxy:
        # High compression = Repetitive/Structured = Stable Well
        encoded = text.encode('utf-8')
        compressed = zlib.compress(encoded)
        stability = 1.0 - (len(compressed) / max(len(encoded), 1))
        return max(0.0, min(stability, 1.0))

    @staticmethod
    def calculate_temperature(text: str) -> float:
        """
        Extracts 'Temperature' (H) from information mass.
        Temperature represents the 'heat' of the manifold. 
        Higher entropy = Higher Temperature.
        """
        if not text:
            return 0.0
        
        # Normalized Shannon Entropy (0.0 to 1.0 range approx)
        # Using 8.0 as max possible ASCII entropy for normalization
        h = LLMGeometrics.calculate_entropy(text)
        return h / 8.0

    @staticmethod
    def calculate_power(difficulty: int, latency_ms: float) -> float:
        """
        Calculates Computational Power (P = W/t).
        W = 2^Difficulty (Work required for mining).
        t = Latency in seconds.
        
        High Power = Fast resolution of complex manifold.
        Low Power = High friction or stalling.
        """
        work = 2 ** difficulty
        time_s = max(latency_ms / 1000.0, 0.001)
        return work / time_s

    @classmethod
    def score_difficulty(cls, data: str, base_difficulty: int = 2, latency_ms: float = 0) -> int:
        """
        Derives an integer difficulty (leading zeros) from the geometric metrics.
        
        Now considers Temporal Friction: if the API took a long time, 
        the manifold is 'stretching', increasing the required effort.
        """
        try:
            # Parse structured data if it's a JSON string
            structured_data = json.loads(data)
            content = structured_data.get('content', data)
            prompt = structured_data.get('prompt', '')
        except:
            content = data
            prompt = ''

        E = cls.calculate_energy(content)
        H = cls.calculate_entropy(content)
        
        if prompt:
            kappa = cls.calculate_curvature(prompt, content)
        else:
            kappa = 0.5 
            
        # Geometric complexity score G
        G = (E * H * (1 + kappa))
        
        # Temporal Friction Factor (F)
        # If latency is > 2 seconds, we consider the manifold to be 'heavy'
        latency_s = latency_ms / 1000.0
        friction = 1.0 + (math.log10(max(latency_s, 1.0)) * 0.5)
        
        # Difficulty offset with friction
        difficulty_offset = int(math.log2(max(G * friction, 1.0)) * 1.5)
        
        final_difficulty = base_difficulty + difficulty_offset
        return max(1, min(final_difficulty, 6))

    @classmethod
    def get_metrics(cls, input_text: str, output_text: str) -> Dict[str, float]:
        """Returns a full suite of metrics for visualization."""
        return {
            "energy": cls.calculate_energy(output_text),
            "entropy": cls.calculate_entropy(output_text),
            "curvature": cls.calculate_curvature(input_text, output_text),
            "difficulty": cls.score_difficulty(json.dumps({
                "content": output_text,
                "prompt": input_text
            }))
        }
