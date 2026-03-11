package com.cocoon.controller;

import cn.hutool.core.util.StrUtil;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.*;

/**
 * 统一返回结果实体
 */
class CocoonResponse {
    private int score;       // 茧房指数 0-100
    private String level;    // 茧房等级
    private String type;     // 类型标签
    private String desc;     // 分析文字
    private String suggest;  // 破茧建议

    public CocoonResponse(int score, String level, String type, String desc, String suggest) {
        this.score = score;
        this.level = level;
        this.type = type;
        this.desc = desc;
        this.suggest = suggest;
    }

    // Getter方法（序列化需要）
    public int getScore() { return score; }
    public String getLevel() { return level; }
    public String getType() { return type; }
    public String getDesc() { return desc; }
    public String getSuggest() { return suggest; }
}

/**
 * 请求参数接收实体
 */
class CocoonRequest {
    private String content; // 用户粘贴的文本

    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
}

/**
 * 核心业务逻辑Service
 */
@org.springframework.stereotype.Service
class CocoonService {
    // 关键词分类库
    private final Map<String, List<String>> KEYWORD_MAP = new HashMap<>();
    // 所有分类
    private final List<String> ALL_CATEGORIES = Arrays.asList("娱乐", "财经", "观点", "其他");

    /**
     * 初始化关键词库
     */
    public CocoonService() {
        KEYWORD_MAP.put("娱乐", Arrays.asList("娱乐", "综艺", "游戏", "短视频", "追剧", "明星", "直播", "网红", "演唱会"));
        KEYWORD_MAP.put("财经", Arrays.asList("财经", "基金", "股票", "理财", "汇率", "A股", "美股", "债券", "定投"));
        KEYWORD_MAP.put("观点", Arrays.asList("政治", "社会", "新闻", "评论", "政策", "民生", "国际", "时事", "热点"));
    }

    /**
     * 核心分析逻辑
     * @param content 用户输入的文本
     * @return 茧房检测结果
     */
    public CocoonResponse analyzeContent(String content) {
        // 空内容处理
        if (StrUtil.isBlank(content)) {
            return new CocoonResponse(0, "无内容", "内容为空", "未检测到有效内容", "请粘贴你常看的文本后重试");
        }

        // 1. 统计各分类命中次数
        Map<String, Integer> countMap = new HashMap<>();
        countMap.put("娱乐", 0);
        countMap.put("财经", 0);
        countMap.put("观点", 0);
        countMap.put("其他", 0);

        int totalHit = 0;
        // 遍历匹配关键词
        for (Map.Entry<String, List<String>> entry : KEYWORD_MAP.entrySet()) {
            String category = entry.getKey();
            int count = 0;
            for (String keyword : entry.getValue()) {
                if (content.contains(keyword)) {
                    count++;
                    totalHit++;
                }
            }
            countMap.put(category, count);
        }
        // 未命中任何关键词归为其他
        if (totalHit == 0) {
            countMap.put("其他", 1);
        }

        // 2. 计算各分类占比
        Map<String, Double> ratioMap = new HashMap<>();
        int total = countMap.values().stream().mapToInt(Integer::intValue).sum();
        for (String category : ALL_CATEGORIES) {
            ratioMap.put(category, total == 0 ? 0 : (double) countMap.get(category) / total);
        }

        // 3. 计算核心指标
        int score = calculateScore(ratioMap);
        String level = getLevel(score);
        String type = getType(ratioMap);
        String desc = getDesc(ratioMap);
        String suggest = getSuggest(ratioMap);

        return new CocoonResponse(score, level, type, desc, suggest);
    }

    /**
     * 计算茧房分数（0-100，分数越高=茧房越轻）
     */
    private int calculateScore(Map<String, Double> ratioMap) {
        // 统计有命中的分类数
        long hitCategory = ratioMap.values().stream().filter(ratio -> ratio > 0).count();
        // 单一分类最大占比
        double maxRatio = ratioMap.values().stream().max(Double::compare).orElse(0.0);

        Random random = new Random();
        int score;
        if (hitCategory >= 3) {
            // 3类及以上：视野开阔（80-100）
            score = 80 + random.nextInt(20);
        } else if (hitCategory == 2) {
            // 2类：轻度茧房（50-80）
            score = 50 + random.nextInt(30);
        } else {
            // 1类：看占比判断中度/严重
            if (maxRatio > 0.7) {
                // 严重茧房（0-30）
                score = random.nextInt(30);
            } else {
                // 中度茧房（30-50）
                score = 30 + random.nextInt(20);
            }
        }
        return score;
    }

    /**
     * 判定茧房等级
     */
    private String getLevel(int score) {
        if (score >= 80) return "视野开阔";
        if (score >= 50) return "轻度茧房";
        if (score >= 30) return "中度茧房";
        return "严重茧房";
    }

    /**
     * 判定类型标签
     */
    private String getType(Map<String, Double> ratioMap) {
        // 多分类均衡则标为视野开阔
        if (ratioMap.values().stream().filter(r -> r > 0).count() >= 3) {
            return "视野开阔";
        }

        // 找到占比最高的分类
        String maxCategory = ratioMap.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("其他");

        // 类型映射
        Map<String, String> typeMap = new HashMap<>();
        typeMap.put("娱乐", "娱乐宅");
        typeMap.put("财经", "财经控");
        typeMap.put("观点", "观点单一");
        typeMap.put("其他", "深度思考者");
        return typeMap.get(maxCategory);
    }

    /**
     * 生成分析描述
     */
    private String getDesc(Map<String, Double> ratioMap) {
        // 取占比前2的分类
        List<Map.Entry<String, Double>> topCategories = ratioMap.entrySet().stream()
                .filter(e -> e.getValue() > 0)
                .sorted((a, b) -> b.getValue().compareTo(a.getValue()))
                .limit(2)
                .toList();

        if (topCategories.isEmpty()) {
            return "你常看的内容无明显特征";
        } else if (topCategories.size() == 1) {
            return "你常看" + topCategories.get(0).getKey() + "类内容，内容较单一";
        } else {
            return "你常看" + topCategories.get(0).getKey() + "、" + topCategories.get(1).getKey() + "类内容，内容相对均衡";
        }
    }

    /**
     * 生成破茧建议
     */
    private String getSuggest(Map<String, Double> ratioMap) {
        // 取占比最低的2个分类（建议多看）
        List<Map.Entry<String, Double>> minCategories = ratioMap.entrySet().stream()
                .filter(e -> e.getValue() < 0.2)
                .sorted(Map.Entry.comparingByValue())
                .limit(2)
                .toList();

        if (minCategories.isEmpty()) {
            return "你的内容覆盖已很全面，继续保持多元视角";
        } else if (minCategories.size() == 1) {
            return "可以多看" + minCategories.get(0).getKey() + "类内容，打破信息茧房";
        } else {
            return "可以多看" + minCategories.get(0).getKey() + "、" + minCategories.get(1).getKey() + "类内容，拓展认知边界";
        }
    }
}

/**
 * 核心接口Controller
 */
@RestController
@RequestMapping("/api")
public class CocoonController {
    private final CocoonService cocoonService;

    // 构造器注入Service
    public CocoonController(CocoonService cocoonService) {
        this.cocoonService = cocoonService;
    }

    /**
     * 茧房检测核心接口
     * @param request 请求参数（用户输入的文本）
     * @return 检测结果
     */
    @PostMapping("/check-cocoon")
    public CocoonResponse checkCocoon(@RequestBody CocoonRequest request) {
        return cocoonService.analyzeContent(request.getContent());
    }
}