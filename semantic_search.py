"""语义搜索工具类"""

import pickle
import threading

class SemanticSearcher:
    """语义搜索器"""
    
    CATEGORY_NAMES = {
        0: "人物灵感",
        1: "情节灵感",
        2: "对话灵感",
        3: "设定灵感",
        4: "其他",
    }
    
    CATEGORY_COLORS = {
        0: "#8B5CF6",
        1: "#EF4444",
        2: "#3B82F6",
        3: "#10B981",
        4: "#6B7280",
    }
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.model = None
        self.model_loaded = False
        self.load_model()
    
    def load_model(self):
        """加载语义模型（后台线程）"""
        def _load():
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.model_loaded = True
            except ImportError:
                self.model_loaded = False
        
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
    
    def get_embedding(self, text):
        """获取文本向量嵌入"""
        if not self.model_loaded:
            return self._simple_hash_embedding(text)
        
        try:
            embedding = self.model.encode(text)
            return pickle.dumps(embedding)
        except Exception:
            return self._simple_hash_embedding(text)
    
    def _simple_hash_embedding(self, text):
        """简单哈希嵌入（降级方案）"""
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        dim = 384
        embedding = []
        for i in range(dim):
            embedding.append((hash_val >> (i * 4)) % 256 / 255.0)
        return pickle.dumps(embedding)
    
    def cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        try:
            v1 = pickle.loads(vec1)
            v2 = pickle.loads(vec2)
            
            if isinstance(v1, list) and isinstance(v2, list):
                pass
            else:
                try:
                    v1 = v1.tolist()
                    v2 = v2.tolist()
                except AttributeError:
                    return 0.0
            
            if len(v1) != len(v2):
                return 0.0
            
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = (sum(a * a for a in v1)) ** 0.5
            norm2 = (sum(b * b for b in v2)) ** 0.5
            
            return dot / (norm1 * norm2) if (norm1 > 0 and norm2 > 0) else 0.0
        except Exception:
            return 0.0
    
    def semantic_search(self, query, top_k=10):
        """语义搜索"""
        query_embedding = self.get_embedding(query)
        
        inspirations = self.db.get_inspirations_with_embeddings()
        
        results = []
        for insp in inspirations:
            if insp.get('embedding'):
                sim = self.cosine_similarity(query_embedding, insp['embedding'])
                if sim > 0.1:
                    results.append({
                        'type': 'inspiration',
                        'id': insp['id'],
                        'content': insp['content'],
                        'category': insp.get('category', 0),
                        'category_name': self.CATEGORY_NAMES.get(insp.get('category', 0), '其他'),
                        'tags': insp.get('tags', ''),
                        'is_used': insp.get('is_used', 0),
                        'created_at': insp.get('created_at', ''),
                        'similarity': sim,
                    })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def hybrid_search(self, query, top_k=10):
        """混合搜索（关键词+语义）"""
        keyword_results = self.db.search_inspirations_keyword(query)
        semantic_results = self.semantic_search(query, top_k)
        
        all_results = []
        
        for insp in keyword_results[:top_k]:
            all_results.append({
                'type': 'inspiration',
                'id': insp['id'],
                'content': insp['content'],
                'category': insp.get('category', 0),
                'category_name': self.CATEGORY_NAMES.get(insp.get('category', 0), '其他'),
                'tags': insp.get('tags', ''),
                'is_used': insp.get('is_used', 0),
                'created_at': insp.get('created_at', ''),
                'similarity': 0.8,
                'match_type': 'keyword',
            })
        
        for res in semantic_results:
            exists = False
            for r in all_results:
                if r['id'] == res['id']:
                    r['similarity'] = max(r['similarity'], res['similarity'])
                    exists = True
                    break
            if not exists:
                res['match_type'] = 'semantic'
                all_results.append(res)
        
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        return all_results[:top_k]
    
    def search_events(self, query):
        """搜索事件（关键词+语义）"""
        events = self.db.get_all_events()
        
        query_embedding = self.get_embedding(query)
        results = []
        
        for ev in events:
            text = f"{ev.get('title', '')} {ev.get('content', '')}"
            
            sim = 0.0
            if ev.get('embedding'):
                sim = self.cosine_similarity(query_embedding, ev['embedding'])
            
            keyword_match = 0
            if query.lower() in text.lower():
                keyword_match = 0.5
            
            combined_score = max(sim, keyword_match)
            
            if combined_score > 0.1:
                results.append({
                    'type': 'event',
                    'id': ev['id'],
                    'title': ev.get('title', ''),
                    'content': ev.get('content', ''),
                    'timestamp': ev.get('timestamp', ''),
                    'character_name': ev.get('character_name', ''),
                    'similarity': combined_score,
                })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:10]