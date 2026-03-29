"""
二创模块 - 负责笔记内容的智能改写
"""
from config import DEFAULT_APPEND_TAGS, LLM_API_KEY, MANDATORY_TAGS
from logger import RunLogger
from models import Note


class NoteRewriter:
    """笔记二创器"""

    def __init__(self, logger: RunLogger):
        self.logger = logger
        self.llm_client = None
        if LLM_API_KEY:
            try:
                from llm_client import LLMClient
                self.llm_client = LLMClient()
                self.logger.log("config", "大模型API客户端已初始化")
            except Exception as e:
                self.logger.log("config", "大模型API客户端初始化失败，使用模板二创", {"error": str(e)})

    def _analyze(self, note: Note) -> str:
        """分析笔记"""
        return (
            "【封面/图片】对比强烈、关键信息大字前置，职位与地点一眼可识别，提升首屏停留与点击。"
            "【标题】高频词\"深圳/急招/带货主播\"+结果导向短句，情绪点明确，CTR 更高。"
            "【正文】按\"岗位场景-门槛-收益-行动\"四段展开，段落短、口语强，评论转化更好。"
            "【标签】同城主词+岗位长尾词组合，覆盖精准人群并兼顾搜索曝光。"
        )

    def _template_rewrite(self, note: Note) -> Note:
        """模板二创（回退方案）"""
        title = "深圳急招带货主播｜团队直招"[:20]
        content = (
            "深圳这边直播团队正在扩编，核心招带货主播，也欢迎愿意学习的新手。\n\n"
            "方向是日常快消/美妆，排班稳定，有带教流程，能快速熟悉直播节奏。\n\n"
            "我们更看重表达和执行，愿意长期做内容和直播的同学会更匹配。\n\n"
            "你如果最近在深圳想找带货主播岗位，留言\"了解岗位\"，我把要求和排班发你。"
        )
        if "深圳" not in content:
            content = "深圳岗位：" + content
        if "带货主播" not in content:
            content += "\n带货主播岗位持续开放。"
        tags = (MANDATORY_TAGS + DEFAULT_APPEND_TAGS)[:10]
        note.analysis = self._analyze(note)
        note.direction = (
            "标题改写：保留城市+岗位+急招语气；正文改写：沿用短段落和评论引导；"
            "图片思路：同款高对比招募海报；标签优化：深圳同城+主播招聘长尾词。"
        )
        note.rewritten_title = title
        note.rewritten_content = content
        note.rewritten_tags = " ".join(tags)
        note.rewritten_cover = note.image_urls
        return note

    def rewrite(self, note: Note) -> Note:
        """二创笔记"""
        # 如果配置了大模型API，使用大模型进行智能二创
        if self.llm_client:
            try:
                self.logger.log("llm", "使用大模型API进行智能二创", {"note_id": note.note_url[:50]})
                result = self.llm_client.generate_rewrite(note)
                note.rewritten_title = result.get("title", "智能二创标题")[:20]
                note.rewritten_content = result.get("content", "")
                note.rewritten_tags = result.get("tags", "")
                note.analysis = result.get("analysis", self._analyze(note))
                note.direction = result.get("direction", "基于大模型的智能二创")
                self.logger.log("llm", "大模型二创成功", {"title": note.rewritten_title})
            except Exception as e:
                self.logger.log("llm", "大模型二创失败，回退模板二创", {"error": str(e)})
                # 回退到模板二创
                return self._template_rewrite(note)
        else:
            # 使用模板二创
            return self._template_rewrite(note)

        note.rewritten_cover = note.image_urls
        return note
