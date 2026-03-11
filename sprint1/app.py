import os
import sys
import logging
from datetime import datetime
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ======================== 初始化配置 ========================
# 加载环境变量
load_dotenv()

# 创建日志目录
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"travelgo_{datetime.now().strftime('%Y%m%d')}.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('travelgo-backend')

# 初始化Flask应用
app = Flask(__name__)
# 解决跨域问题（允许所有前端域名访问，生产环境可指定具体域名）
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 初始化阿里云百炼客户端
try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    logger.info("阿里云百炼客户端初始化成功")
except Exception as e:
    client = None
    logger.error(f"阿里云百炼客户端初始化失败: {str(e)}")

# ======================== 工具函数 ========================
def validate_travel_params(params: dict) -> tuple[bool, str]:
    """
    验证旅行方案参数的合法性
    :param params: 前端传递的参数字典
    :return: (是否合法, 错误信息)
    """
    # 验证出发地
    from_place = params.get('from', '').strip()
    if not from_place:
        return False, "出发地不能为空"
    
    # 验证人数（正整数）
    try:
        people = int(params.get('people', 2))
        if people < 1:
            return False, "出行人数必须大于0"
    except ValueError:
        return False, "出行人数必须是有效数字"
    
    # 验证天数（正整数）
    try:
        days = int(params.get('days', 2))
        if days < 1:
            return False, "游玩天数必须大于0"
    except ValueError:
        return False, "游玩天数必须是有效数字"
    
    # 验证预算类型
    budget = params.get('budget', '经济型')
    if budget not in ['经济型', '舒适型', '高端型']:
        return False, "预算类型只能是：经济型/舒适型/高端型"
    
    return True, ""

def build_travel_prompt(params: dict) -> str:
    """
    构建AI生成旅行方案的提示词
    :param params: 验证后的参数字典
    :return: 格式化的提示词
    """
    from_place = params.get('from')
    to_place = params.get('to', '澳门').strip() or '澳门'
    people = int(params.get('people', 2))
    days = int(params.get('days', 2))
    budget = params.get('budget', '经济型')
    
    prompt = f"""
你是一位专业的旅行规划师，擅长根据用户需求定制详细、实用、符合预算的旅行方案。
请为用户生成一份{days}天{budget}的{to_place}旅行方案，具体要求如下：

【基础信息】
- 出发地：{from_place}
- 目的地：{to_place}
- 出行人数：{people}人
- 预算类型：{budget}（经济型=高性价比、舒适型=便捷舒适、高端型=豪华体验）

【方案要求】
1. 结构清晰：包含「行程总览」「每日详细行程」「预算明细」「避坑建议」四个核心模块；
2. 内容详细：每日行程需明确时间段（上午/中午/下午/晚上）、具体景点、推荐美食、交通方式；
3. 预算精准：给出每个模块的具体费用参考（人均），符合对应预算类型的消费水平；
4. 特色突出：结合目的地本地特色，给出专属建议（如澳门的葡式美食、赌场周边注意事项等）；
5. 格式规范：使用Markdown排版，分标题、列表展示，语言简洁易懂，避免冗余。
    """.strip()
    
    return prompt

# ======================== API接口 ========================
@app.route('/api/health', methods=['GET'])
def health_check():
    """
    健康检查接口：用于验证服务是否正常运行
    """
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client_ready": client is not None,
        "python_version": sys.version,
        "service_name": "TravelGo AI Travel Plan Service"
    }), 200

@app.route('/api/generate-travel-plan', methods=['POST'])
def generate_travel_plan():
    """
    生成旅行方案的核心接口
    请求方式：POST
    请求体：JSON格式，包含from/to/people/days/budget
    返回：JSON格式，包含是否成功、旅行方案内容/错误信息
    """
    # 1. 记录请求日志
    logger.info(f"收到生成旅行方案请求: {request.remote_addr} - {request.json}")
    
    # 2. 验证请求格式
    if not request.is_json:
        logger.error("请求格式错误：非JSON格式")
        return jsonify({
            "success": False,
            "message": "请求格式错误，请使用JSON格式"
        }), 400
    
    # 3. 验证参数合法性
    params = request.get_json()
    is_valid, error_msg = validate_travel_params(params)
    if not is_valid:
        logger.error(f"参数验证失败: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 400
    
    # 4. 验证AI客户端是否就绪
    if not client:
        logger.error("AI客户端未初始化，无法生成方案")
        return jsonify({
            "success": False,
            "message": "AI服务未就绪，请检查API Key配置或稍后重试"
        }), 500
    
    try:
        # 5. 构建提示词
        prompt = build_travel_prompt(params)
        logger.info(f"生成提示词完成，长度：{len(prompt)}")
        
        # 6. 调用阿里云百炼API
        completion = client.chat.completions.create(
            model="qwen3.5-flash",  # 可选：qwen-turbo（轻量）/qwen-plus（均衡）/qwen-max（高性能）
            messages=[
                {"role": "system", "content": "你是专业的旅行规划师，只输出旅行方案，不输出无关内容"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,    # 生成多样性（0-1，值越高越灵活）
            max_tokens=2000,    # 最大生成字数
            top_p=0.9,          # 采样概率
            stream=False        # 非流式返回
        )
        
        # 7. 提取AI响应内容
        plan_content = completion.choices[0].message.content.strip()
        logger.info(f"AI生成方案成功，内容长度：{len(plan_content)}")
        
        # 8. 返回成功结果
        return jsonify({
            "success": True,
            "plan": plan_content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
    
    except AuthenticationError:
        logger.error("API Key认证失败：无效的Key或权限不足")
        return jsonify({
            "success": False,
            "message": "API Key认证失败，请检查Key是否正确"
        }), 401
    
    except RateLimitError:
        logger.error("API调用频率超限：请稍后再试")
        return jsonify({
            "success": False,
            "message": "AI服务调用频率超限，请10分钟后再试"
        }), 429
    
    except APIConnectionError:
        logger.error("API连接失败：网络问题或服务不可用")
        return jsonify({
            "success": False,
            "message": "无法连接到AI服务，请检查网络或稍后重试"
        }), 503
    
    except APIError as e:
        logger.error(f"AI API返回错误：{e}")
        return jsonify({
            "success": False,
            "message": f"AI服务返回错误：{e.message}"
        }), 500
    
    except Exception as e:
        logger.error(f"生成旅行方案异常：{str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"服务器内部错误：{str(e)}"
        }), 500

# ======================== 启动服务 ========================
if __name__ == '__main__':
    # 从环境变量读取服务配置
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    
    # 启动Flask服务
    logger.info(f"启动TravelGo后端服务：http://{host}:{port}")
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True  # 开启多线程处理请求
    )





# ======================== 新增：行程保存与优化接口 ========================
@app.route('/api/save-itinerary', methods=['POST'])
def save_itinerary():
    """
    保存用户自定义行程，并生成优化方案
    """
    if not request.is_json:
        return jsonify({
            "success": False,
            "message": "请求格式错误，请使用JSON格式"
        }), 400
    
    params = request.get_json()
    logger.info(f"收到行程保存请求: {params}")
    
    # 验证核心参数
    if not params.get('itinerary') or not isinstance(params.get('itinerary'), dict):
        return jsonify({
            "success": False,
            "message": "行程数据格式错误"
        }), 400
    
    try:
        # 1. 生成行程ID（简单实现，生产环境可用UUID）
        import uuid
        plan_id = str(uuid.uuid4())[:8]
        
        # 2. 构建优化提示词（基于用户选点）
        itinerary = params.get('itinerary')
        budget = params.get('budget', '经济型')
        people = params.get('people', 2)
        
        # 拼接行程描述
        itinerary_desc = ""
        for day, points in itinerary.items():
            if points:
                itinerary_desc += f"\n第{day}天：{', '.join([p['name'] for p in points])}"
        
        # 构建提示词
        prompt = f"""
你是专业的旅行规划师，需要优化用户自定义的澳门行程，要求如下：
1. 基础信息：{people}人，{budget}预算
2. 用户自定义行程：{itinerary_desc}
3. 优化要求：
   - 调整行程顺序，优化交通路线，减少折返
   - 补充每个点位的游玩时长、推荐美食、费用参考
   - 按Markdown格式输出，包含行程总览、每日详情、预算明细
   - 保留用户选择的核心点位，仅优化顺序和补充信息
        """.strip()
        
        # 3. 调用AI生成优化方案
        completion = client.chat.completions.create(
            model="qwen3.5-flash",
            messages=[
                {"role": "system", "content": "你是专业的旅行规划师，只输出优化后的行程方案"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # 4. 保存行程（示例：内存存储，生产环境可存数据库）
        # 实际项目中可使用Redis/MySQL存储plan_id和对应的方案
        global saved_plans
        if 'saved_plans' not in globals():
            saved_plans = {}
        saved_plans[plan_id] = {
            "itinerary": itinerary,
            "optimized_plan": completion.choices[0].message.content.strip(),
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({
            "success": True,
            "planId": plan_id,
            "message": "行程保存并优化成功"
        }), 200
        
    except Exception as e:
        logger.error(f"保存行程异常：{str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"保存失败：{str(e)}"
        }), 500

# 新增：根据plan_id获取优化后的方案
@app.route('/api/get-optimized-plan/<plan_id>', methods=['GET'])
def get_optimized_plan(plan_id):
    """
    获取优化后的行程方案
    """
    global saved_plans
    if 'saved_plans' not in globals() or plan_id not in saved_plans:
        return jsonify({
            "success": False,
            "message": "方案不存在"
        }), 404
    
    return jsonify({
        "success": True,
        "plan": saved_plans[plan_id]['optimized_plan'],
        "itinerary": saved_plans[plan_id]['itinerary']
    }), 200