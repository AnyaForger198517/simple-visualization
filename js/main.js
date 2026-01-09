// 全局变量
let currentDataType = "post_count"; // 趋势图默认发帖数
let currentYear = "all"; // 趋势图默认全部年份
let currentChartType = "trend"; // 默认图表类型：趋势图
let currentTopCount = 5; // 饼图默认TOP数量：5
let showOtherCategory = true; // 饼图是否显示"其他"类别

// 右侧样例文章浏览状态
let currentDomainArticles = [];
let currentArticleIndex = 0;
let currentDomainName = "";

// 双全派数据
let conservativeData = {};
let liberalData = {};
// 年份范围：2008-2021
const yearRange = Array.from({length: 14}, (_, i) => 2008 + i);
// 图片指定的莫兰迪色系（优先级：前6个，超过则循环）
const morandiColors = [
    "#8d9fbd", "#a1b08b", "#e6ae7f", 
    "#b2b6bc", "#e9d981", "#e7abb0"
];

// === 词云相关 ===
// === 词云相关全局变量 ===
const topicCache = {
    Conservative: {},
    Liberal: {}
};

// === 1. 加载单月主题数据（缓存优化） ===
async function loadMonthlyTopic(party, month) {
    if (topicCache[party][month]) {
        return topicCache[party][month];
    }
    const res = await fetch(`./data/wordcloud_data/${party}/${month}.json`);
    const json = await res.json();
    topicCache[party][month] = json;
    return json;
}

// === 2. 关键词权重聚合（核心：确保两党数据都被统计） ===
async function aggregateKeywords(months) {
    const wordMap = new Map();
    let maxCon = 0;
    let maxLib = 0;

    // 遍历两党+所有选中月份
    for (const party of ["Conservative", "Liberal"]) {
        for (const month of months) {
            try {
                const data = await loadMonthlyTopic(party, month);
                const total = data.total_articles || 0; // 兼容无数据情况
                if (total === 0) continue;

                // 遍历主题摘要，计算关键词权重
                (data.deep_topics_summary || []).forEach(topic => {
                    const ratio = (topic.importance_ratio || 0) / 100;
                    if (ratio <= 0) return;

                    const perWord = total * ratio / (topic.core_keywords?.length || 1);
                    (topic.core_keywords || []).forEach(word => {
                        if (!word || word.trim() === "") return; // 过滤空关键词

                        if (!wordMap.has(word)) {
                            wordMap.set(word, { con: 0, lib: 0 });
                        }

                        const current = wordMap.get(word);
                        if (party === "Conservative") {
                            current.con += perWord;
                            maxCon = Math.max(maxCon, current.con); // 更新保守派最大权重
                        } else {
                            current.lib += perWord;
                            maxLib = Math.max(maxLib, current.lib); // 更新自由派最大权重
                        }
                        wordMap.set(word, current);
                    });
                });
            } catch (error) {
                console.warn(`加载${party}${month}主题数据失败:`, error);
                continue; // 单个月份失败不影响整体
            }
        }
    }

    // 调试信息：输出统计结果
    console.log(`关键词聚合完成 - 总词汇数:${wordMap.size}, maxCon:${maxCon.toFixed(2)}, maxLib:${maxLib.toFixed(2)}`);

    // 转换为词云所需格式（包含两党权重和极值）
    return Array.from(wordMap.entries())
        .filter(([_, v]) => v.con + v.lib > 0.1) // 过滤极低权重词汇
        .map(([text, v]) => ({
            text: text.trim(),
            con: v.con,
            lib: v.lib,
            value: v.con + v.lib, // 总权重
            maxCon: maxCon || 1, // 避免除以0
            maxLib: maxLib || 1  // 避免除以0
        }));
}

// === 3. 交并集布局核心配置 ===
function initUnionWordCloudLayout() {
    return {
        // 计算三区域位置（基于SVG实际尺寸）
        getRegionParams(svgWidth, svgHeight) {
            const regionWidth = svgWidth / 3;
            return {
                conservative: { // 左侧：保守派专属
                    xRange: [regionWidth * 0.05, regionWidth * 0.95],
                    yRange: [svgHeight * 0.1, svgHeight * 0.9],
                    baseColor: "#409eff"
                },
                intersection: { // 中间：两党交集
                    xRange: [regionWidth * 1.05, regionWidth * 1.95],
                    yRange: [svgHeight * 0.1, svgHeight * 0.9],
                    baseColor: "#8c8c8c"
                },
                liberal: { // 右侧：自由派专属
                    xRange: [regionWidth * 2.05, regionWidth * 2.95],
                    yRange: [svgHeight * 0.1, svgHeight * 0.9],
                    baseColor: "#e6a23c"
                }
            };
        },

        // 生成不重叠的位置（关键：避免词汇挤在一起）
        generatePosition(xRange, yRange, existingPositions, wordSize) {
            const padding = wordSize * 1.5; // 词汇间距（根据大小调整）
            let attempts = 0;
            let x, y;

            do {
                // 在区域内随机生成坐标
                x = xRange[0] + Math.random() * (xRange[1] - xRange[0]);
                y = yRange[0] + Math.random() * (yRange[1] - yRange[0]);
                attempts++;
            } while (
                attempts < 150 && // 最多尝试150次，避免死循环
                existingPositions.some(pos => 
                    Math.hypot(x - pos.x, y - pos.y) < padding + pos.size / 2
                )
            );

            return { x, y };
        }
    };
}

// === 4. 词汇分类（保守派专属/交集/自由派专属） ===
function classifyWords(words) {
    const conWords = [];
    const interWords = [];
    const libWords = [];
    // 专属阈值：从0.75调整为0.8（数值越高，中间渐变区域越大）
    const exclusiveThreshold = 0.8; 
    words.forEach(word => {
        const total = word.con + word.lib;
        if (total === 0) return;
        const conRatio = word.con / total;
        const libRatio = word.lib / total;
        if (conRatio >= exclusiveThreshold) {
            conWords.push(word); // 保守派专属（占比≥80%）
        } else if (libRatio >= exclusiveThreshold) {
            libWords.push(word); // 自由派专属（占比≥80%）
        } else {
            interWords.push(word); // 中间渐变区域（其余情况）
        }
    });
    // 按权重排序（权重高的词汇更大、更靠中心）
    const sortedCon = conWords.sort((a, b) => b.value - a.value);
    const sortedInter = interWords.sort((a, b) => b.value - a.value);
    const sortedLib = libWords.sort((a, b) => b.value - a.value);
    // 调试信息
    console.log(`词汇分类结果 - 保守派:${sortedCon.length}, 交集:${sortedInter.length}, 自由派:${sortedLib.length}`);
    
    return [sortedCon, sortedInter, sortedLib];
}

// === 5. 绘制区域分隔线和标题 ===
function drawRegionDividers(svg, width, height) {
    const regionWidth = width / 3;
    const g = svg.append("g").attr("class", "region-dividers");

    // 垂直分隔线（虚线）
    g.append("line")
        .attr("x1", regionWidth)
        .attr("y1", height * 0.08)
        .attr("x2", regionWidth)
        .attr("y2", height * 0.92)
        .style("stroke", "#e5e7eb")
        .style("stroke-width", 2)
        .style("stroke-dasharray", "8,4");

    g.append("line")
        .attr("x1", regionWidth * 2)
        .attr("y1", height * 0.08)
        .attr("x2", regionWidth * 2)
        .attr("y2", height * 0.92)
        .style("stroke", "#e5e7eb")
        .style("stroke-width", 2)
        .style("stroke-dasharray", "8,4");

    // 区域标题
    const titles = [
        { text: "保守派专属话题", x: regionWidth / 2, color: "#409eff" },
        { text: "两党共同话题", x: regionWidth * 1.5, color: "#8c8c8c" },
        { text: "自由派专属话题", x: regionWidth * 2.5, color: "#e6a23c" }
    ];

    titles.forEach(title => {
        g.append("text")
            .attr("x", title.x)
            .attr("y", height * 0.05)
            .attr("text-anchor", "middle")
            .style("font-size", "15px")
            .style("font-weight", "600")
            .style("fill", title.color)
            .style("font-family", "Microsoft YaHei")
            .text(title.text);
    });
}

// === 6. 词汇颜色计算（高对比+离散梯度+分层区分） ===
function getWordColor(word, region) {
    // 1. 定义基础色（严格匹配需求：保守派蓝、自由派橙）
    const baseColors = {
        conservative: "#1890ff", // 保守派主色：深蓝色
        liberal: "#faad14",      // 自由派主色：深橙色
        intersectionStart: "#1890ff", // 交集渐变起点（蓝）
        intersectionEnd: "#faad14"    // 交集渐变终点（橙）
    };
    // 2. 计算权重分位数（用于专属区域的颜色深浅梯度）
    function getColorIndex(weight, maxWeight) {
        if (maxWeight === 0) return 0;
        const ratio = weight / maxWeight;
        // 5个离散梯度（权重越高颜色越深）
        return Math.min(Math.floor(ratio * 5), 4);
    }
    // 3. 专属区域：固定色系+深浅梯度（保持辨识度）
    if (region === "conservative") {
        // 保守派专属：深蓝色系渐变（从浅到深）
        const colorGradients = [
            "#b3d9f2", // 浅蓝
            "#73b3e6", 
            "#3689c9", 
            "#1a6fb4", 
            "#0f528a"  // 深蓝（主色加深）
        ];
        const index = getColorIndex(word.con, word.maxCon);
        return colorGradients[index];
    } else if (region === "liberal") {
        // 自由派专属：深橙色系渐变（从浅到深）
        const colorGradients = [
            "#ffd9b3", // 浅橙
            "#ffb380", 
            "#ff8c4d", 
            "#e66a2c", 
            "#c44d1c"  // 深橙（主色加深）
        ];
        const index = getColorIndex(word.lib, word.maxLib);
        return colorGradients[index];
    } else {
        // 4. 交集区域：蓝橙渐变（核心适配需求）
        const totalWeight = word.con + word.lib;
        if (totalWeight === 0) return "#8c8c8c"; // 异常值兜底
        
        // 计算渐变比例：保守派权重占比 → 0（全橙）~1（全蓝）
        const blueRatio = word.con / totalWeight;
        // 使用d3插值函数实现平滑渐变
        return d3.interpolate(baseColors.intersectionStart, baseColors.intersectionEnd)(1 - blueRatio);
    }
}
// === 7. 绘制单个区域的词汇 ===
function drawRegionWords(svg, words, region, existingPositions, layout) {
    const g = svg.append("g").attr("class", `region-${region}`);
    const maxValue = words.length > 0 ? d3.max(words, d => d.value) : 1;
    words.forEach(word => {
        // 计算字体大小（12-60px，基于总权重）
        const wordSize = Math.max(12, Math.min(60, 12 + (word.value / maxValue) * 48));
        // 生成不重叠位置
        const position = layout.generatePosition(
            region.xRange,
            region.yRange,
            existingPositions,
            wordSize
        );
        // 记录已占用位置（用于后续词汇防重叠）
        existingPositions.push({ ...position, size: wordSize });
        // 随机旋转角度（-15°~15°，避免呆板）
        const rotate = Math.floor(Math.random() * 31) - 15;
        // 计算透明度（权重越高越不透明，最低0.9确保渐变清晰）
        const opacity = Math.max(0.9, word.weight || 0.95);
        // 绘制词汇
        g.append("text")
            .attr("x", position.x)
            .attr("y", position.y)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .attr("transform", `rotate(${rotate} ${position.x} ${position.y})`)
            .style("font-size", `${wordSize}px`)
            .style("font-weight", word.value / maxValue > 0.7 ? "bold" : "normal")
            .style("fill", getWordColor(word, region)) // 使用优化后的颜色逻辑
            .style("opacity", opacity)
            .style("cursor", "pointer")
            .text(word.text)
            .datum(word)
            // 悬浮交互（保持原有逻辑）
            .on("mouseover", function(event, d) {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .style("font-size", `${wordSize * 1.3}px`)
                    .style("opacity", 1);
                const tooltip = d3.select("body").select(".tooltip").empty()
                    ? d3.select("body").append("div").attr("class", "tooltip")
                    : d3.select("body").select(".tooltip");
                tooltip.transition().duration(200).style("opacity", 0.95);
                tooltip.html(`
                    <div style="font-weight:600;margin-bottom:4px;">${d.text}</div>
                    保守派权重：${d.con.toFixed(2)}<br/>
                    自由派权重：${d.lib.toFixed(2)}<br/>
                    总权重：${d.value.toFixed(2)}
                `)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 20) + "px");
            })
            .on("mouseout", function() {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .style("font-size", `${wordSize}px`)
                    .style("opacity", opacity);
                d3.select("body").select(".tooltip")
                    .transition()
                    .duration(200)
                    .style("opacity", 0);
            });
    });
}

// === 8. 交并集词云主绘制函数 ===
function drawUnionWordCloud(words, svg) {
    // 清空原有内容
    svg.selectAll("*").remove();
    const width = svg.node().clientWidth;
    const height = svg.node().clientHeight;
    const layout = initUnionWordCloudLayout();
    const regions = layout.getRegionParams(width, height);
    const existingPositions = []; // 记录所有已占用位置（跨区域防重叠）

    // 绘制分隔线和标题
    drawRegionDividers(svg, width, height);

    // 分类词汇
    const [conWords, interWords, libWords] = classifyWords(words);

    // 调试信息：输出每个区域的前5个词
    console.log("保守派专属词汇(前5):", conWords.slice(0, 5).map(w => `${w.text}(${w.con.toFixed(1)})`));
    console.log("交集词汇(前5):", interWords.slice(0, 5).map(w => `${w.text}(con:${w.con.toFixed(1)}, lib:${w.lib.toFixed(1)})`));
    console.log("自由派专属词汇(前5):", libWords.slice(0, 5).map(w => `${w.text}(${w.lib.toFixed(1)})`));

    // 绘制三个区域的词汇（顺序：保守派→交集→自由派）
    drawRegionWords(svg, conWords, regions.conservative, existingPositions, layout);
    drawRegionWords(svg, interWords, regions.intersection, existingPositions, layout);
    drawRegionWords(svg, libWords, regions.liberal, existingPositions, layout);

    // 无数据提示
    if (conWords.length === 0 && interWords.length === 0 && libWords.length === 0) {
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", height / 2)
            .attr("text-anchor", "middle")
            .style("font-size", "16px")
            .style("fill", "#999")
            .text("暂无关键词数据");
    }
}

// === 9. 词云渲染入口（趋势图刷选后调用） ===
async function renderWordCloudForMonths(months) {
    showWordCloudPanel(); // 切换到词云面板
    const svg = d3.select("#wordCloudSvg");
    try {
        // 加载并聚合关键词
        const words = await aggregateKeywords(months);
        
        // 筛选前120个权重最高的词汇（避免过于拥挤）
        const validWords = words
            .sort((a, b) => b.value - a.value)
            .slice(0, 120)
            .map(word => ({
                ...word,
                weight: word.value / Math.max(word.maxCon, word.maxLib) // 新增权重字段，用于颜色和透明度计算
            }));
        // 绘制交并集词云
        drawUnionWordCloud(validWords, svg);
    } catch (error) {
        console.error("词云渲染失败:", error);
        svg.selectAll("*").remove();
        svg.append("text")
            .attr("x", svg.node().clientWidth / 2)
            .attr("y", svg.node().clientHeight / 2)
            .attr("text-anchor", "middle")
            .style("font-size", "16px")
            .style("fill", "#ff4d4f")
            .text("词云加载失败，请检查数据文件");
    }
}
// === 10. 面板切换辅助函数（保留原有逻辑） ===
function showWordCloudPanel() {
    document.getElementById("wordCloudPanel").style.display = "flex";
    document.getElementById("articleViewer").style.display = "none";
}

function showArticlePanel() {
    document.getElementById("wordCloudPanel").style.display = "none";
    document.getElementById("articleViewer").style.display = "block";
}



// 页面加载初始化
window.onload = async function() {
    try {
        // 1. 初始化图表类型切换
        initChartTypeSwitch();
        // 2. 加载趋势图数据
        await loadDualPartyData();
        // 3. 初始化趋势图控件
        initYearSelector();
        bindTrendButtonEvents();
        // 4. 初始化饼图控件
        bindDomainButtonEvents();
        // 5. 初始化默认图表（趋势图）
        initTimeChart();
        console.log("可视化面板初始化完成");
    } catch (error) {
        console.error("初始化失败：", error);
        alert("数据加载失败，请检查data目录下的文件");
    }
};


// 1. 图表类型切换
function initChartTypeSwitch() {
    const chartTypeBtns = document.querySelectorAll(".chart-type-btn");
    chartTypeBtns.forEach(btn => {
        btn.addEventListener("click", function() {
            // 切换按钮激活状态
            chartTypeBtns.forEach(b => b.classList.remove("active"));
            this.classList.add("active");
            // 更新当前图表类型
            currentChartType = this.dataset.chart;
            // 切换控件显示/隐藏
            document.querySelector(".trend-controls").style.display = currentChartType === "trend" ? "flex" : "none";
            document.querySelector(".domain-controls").style.display = currentChartType === "domain" ? "flex" : "none";
            // 切换图例显示/隐藏
            document.querySelector(".trend-legend").style.display = currentChartType === "trend" ? "flex" : "none";
            // 渲染对应图表
            if (currentChartType === "trend") {
                initTimeChart();
            } else {
                initDualPartyPieChart();
            }
        });
    });
}

// 2. 加载趋势图数据（保守派+自由派）
async function loadDualPartyData() {
    const resCon = await fetch('data/time_statistics_conservative.json');
    conservativeData = await resCon.json();
    const resLib = await fetch('data/time_statistics_liberal.json');
    liberalData = await resLib.json();
}

// 3. 初始化趋势图年份选择器
function initYearSelector() {
    const yearSelect = document.getElementById("yearSelect");
    yearSelect.innerHTML = "";
    // 全部年份选项
    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = "全部年份（2008-2021）";
    yearSelect.appendChild(allOption);
    // 2008-2021年份选项
    yearRange.forEach(year => {
        const option = document.createElement("option");
        option.value = year;
        option.textContent = year + "年";
        yearSelect.appendChild(option);
    });
    // 绑定年份选择事件
    yearSelect.addEventListener("change", function() {
        currentYear = this.value;
        initTimeChart();
    });
}

// 4. 绑定趋势图按钮事件
function bindTrendButtonEvents() {
    // 数据类型切换（发帖数/点赞数/评论数）
    const typeButtons = document.querySelectorAll(".trend-controls .vertical-buttons .btn");
    typeButtons.forEach(btn => {
        btn.addEventListener("click", function() {
            typeButtons.forEach(b => b.classList.remove("active"));
            this.classList.add("active");
            currentDataType = this.dataset.type;
            initTimeChart();
        });
    });
    // 显示全部年份按钮
    document.getElementById("showAllBtn").addEventListener("click", function() {
        currentYear = "all";
        document.getElementById("yearSelect").value = "all";
        initTimeChart();
    });
}

// 5. 绑定饼图按钮事件
function bindDomainButtonEvents() {
    // TOP数量选择
    document.getElementById("topCountSelect").addEventListener("change", function() {
        currentTopCount = Number(this.value);
        showOtherCategory = true; // 重置显示"其他"
        initDualPartyPieChart();
    });
    // 刷新饼图按钮
    document.getElementById("refreshDomainBtn").addEventListener("click", function() {
        showOtherCategory = true; // 重置显示"其他"
        initDualPartyPieChart();
    });
}

// 6. 趋势图数据预处理
function processTimeData() {
    const conDataPoints = [];
    const libDataPoints = [];
    const targetYears = currentYear === "all" ? yearRange : [Number(currentYear)];

    targetYears.forEach(year => {
        const conYearData = conservativeData[year] || {};
        const libYearData = liberalData[year] || {};

        for (let month = 1; month <= 12; month++) {
            const monthStr = month.toString();
            const conMonthData = conYearData[monthStr];
            const libMonthData = libYearData[monthStr];

            if (conMonthData || libMonthData) {
                const dateKey = `${year}-${month.toString().padStart(2, '0')}`;
                conDataPoints.push({
                    date: dateKey,
                    value: conMonthData ? conMonthData[currentDataType] : 0,
                    party: "conservative"
                });
                libDataPoints.push({
                    date: dateKey,
                    value: libMonthData ? libMonthData[currentDataType] : 0,
                    party: "liberal"
                });
            }
        }
    });

    return {
        con: conDataPoints,
        lib: libDataPoints,
        all: [...conDataPoints, ...libDataPoints]
    };
}

// 7. 初始化时间趋势图
function initTimeChart() {
    // 清空旧图表
    d3.select("#mainChart").selectAll("*").remove();

    const container = d3.select(".chart-box");
    const width = container.node().clientWidth;
    const height = container.node().clientHeight;
    const margin = { 
        top: 50,    // 上：预留图例+Y轴label空间
        right: 60,  // 右：预留右侧空白
        bottom: 80, // 下：大幅增大，避免X轴label和折线重叠
        left: 80    // 左：增大，避免Y轴label和折线重叠
    };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // 创建SVG
    const svg = d3.select("#mainChart")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${margin.left}, ${margin.top})`);

    // 预处理数据
    const processedData = processTimeData();
    const conData = processedData.con;
    const libData = processedData.lib;
    const allData = processedData.all;

    // 无数据时提示
    if (allData.length === 0) {
        svg.append("text")
            .attr("x", innerWidth / 2)
            .attr("y", innerHeight / 2)
            .attr("text-anchor", "middle")
            .attr("fill", "#999")
            .text("暂无对应数据");
        return;
    }

    // 定义比例尺
    const xScale = d3.scaleBand()
        .domain(conData.map(d => d.date))
        .range([0, innerWidth])
        .padding(0.1);

    const yMax = d3.max(allData, d => d.value) * 1.1;
    const yScale = d3.scaleLinear()
        .domain([0, yMax])
        .range([innerHeight, 0]);

    // 动态调整X轴刻度密度
    let tickStep = 1;
    const monthCount = conData.length;
    if (monthCount > 24) tickStep = 6;
    else if (monthCount > 12) tickStep = 3;
    else tickStep = 2;

    // 绘制X轴
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", `translate(0, ${innerHeight})`)
        .call(d3.axisBottom(xScale).tickValues(xScale.domain().filter((d, i) => i % tickStep === 0)))
        .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-0.8em")
        .attr("dy", "0.5em");

    // 绘制Y轴
    svg.append("g")
        .attr("class", "y axis")
        .call(d3.axisLeft(yScale).ticks(8))
        .selectAll("text")
        .attr("dx", "0.5em");

    // Y轴标签
    svg.append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", -margin.left + 20)
        .attr("x", -innerHeight / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "#333")
        .attr("font-size", "12px")
        .text(getDataTypeName() + "（双党派对比）");

    // 折线生成器
    const lineGenerator = d3.line()
        .x(d => xScale(d.date) + xScale.bandwidth() / 2)
        .y(d => yScale(d.value));

    // 绘制保守派折线
    svg.append("path")
        .attr("class", "line conservative")
        .attr("d", lineGenerator(conData));

    // 绘制自由派折线
    svg.append("path")
        .attr("class", "line liberal")
        .attr("d", lineGenerator(libData));

    // 绘制保守派数据点
    svg.selectAll(".dot.conservative")
        .data(conData)
        .enter()
        .append("circle")
        .attr("class", "dot conservative")
        .attr("cx", d => xScale(d.date) + xScale.bandwidth() / 2)
        .attr("cy", d => yScale(d.value))
        .attr("r", 3);

    // 绘制自由派数据点
    svg.selectAll(".dot.liberal")
        .data(libData)
        .enter()
        .append("circle")
        .attr("class", "dot liberal")
        .attr("cx", d => xScale(d.date) + xScale.bandwidth() / 2)
        .attr("cy", d => yScale(d.value))
        .attr("r", 3);

    // 提示框
    const tooltip = d3.select("body").select(".tooltip").empty() 
        ? d3.select("body").append("div").attr("class", "tooltip")
        : d3.select("body").select(".tooltip");
    
    // 数值标签（悬浮时显示）
    const valueLabel = svg.append("text")
        .attr("class", "value-label")
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("font-weight", "bold")
        .attr("fill", "#333")
        .style("opacity", 0);

    svg.selectAll(".dot")
        .on("mouseover", function(event, d) {
            const partyName = d.party === "conservative" ? "保守派" : "自由派";
            // 数据点放大
            d3.select(this)
                .transition()
                .duration(200)
                .attr("r", 6);
            
            // 显示数值标签
            valueLabel
                .attr("x", xScale(d.date) + xScale.bandwidth() / 2)
                .attr("y", yScale(d.value) - 10)
                .text(d.value)
                .transition()
                .duration(200)
                .style("opacity", 1);
            
            // 提示框
            tooltip.transition().duration(200).style("opacity", 0.9);
            tooltip.html(`
                ${d.date}<br/>
                ${partyName} ${getDataTypeName()}: ${d.value}
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseout", function() {
            // 数据点恢复
            d3.select(this)
                .transition()
                .duration(200)
                .attr("r", 3);
            
            // 隐藏数值标签
            valueLabel
                .transition()
                .duration(200)
                .style("opacity", 0);
            
            tooltip.transition().duration(200).style("opacity", 0);
        });

        // === Brush：时间刷选 ===
        const brush = d3.brushX()
            .extent([[0, 0], [innerWidth, innerHeight]])
            .on("end", function(event) {
                if (!event.selection) return;

                const [x0, x1] = event.selection;

                const selectedMonths = xScale.domain().filter(d => {
                    const x = xScale(d) + xScale.bandwidth() / 2;
                    return x >= x0 && x <= x1;
                });

                if (selectedMonths.length) {
                    console.log("选中的月份：", selectedMonths.join(", "));
                    renderWordCloudForMonths(selectedMonths);
                }
            });

        svg.append("g")
            .attr("class", "brush")
            .call(brush);
}

// 8. 加载单党派域名数据
async function loadSinglePartyDomainData(party) {
    const fileName = `top${currentTopCount}_domains_${party}.json`;
    const res = await fetch(`data/${fileName}`);
    return await res.json();
}

// 9. 初始化双党派并列饼图
async function initDualPartyPieChart() {
    // 清空旧图表
    d3.select("#mainChart").selectAll("*").remove();

    try {
        // 1. 加载双党派数据
        const conDomainData = await loadSinglePartyDomainData("Conservative");
        const libDomainData = await loadSinglePartyDomainData("Liberal");

        // 2. 容器尺寸
        const container = d3.select(".chart-box");
        const width = container.node().clientWidth;
        const height = container.node().clientHeight;

        // 3. 创建双饼图容器组
        const svg = d3.select("#mainChart")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("class", "pie-chart-group");

        // 4. 绘制保守派饼图
        drawSinglePieChart(svg, conDomainData, "Conservative", 0, width, height);
        
        // 5. 绘制自由派饼图
        drawSinglePieChart(svg, libDomainData, "Liberal", 1, width, height);

    } catch (error) {
        console.error("双党派饼图加载失败：", error);
        alert(`加载TOP${currentTopCount}域名数据失败，请检查data目录下的文件是否存在`);
    }
}

// 10. 绘制单个党派饼图（核心：防文本重叠 + 指定莫兰迪色 + 交互增强）
function drawSinglePieChart(svg, domainData, title, partyIndex, totalWidth, totalHeight) {
    // 1. 数据处理
    const topKey = currentTopCount === 5 ? "top5_domains" : "top10_domains";
    const otherKey = currentTopCount === 5 ? "other_than_top5" : "other_than_top10";
    const topDomains = domainData[topKey] || [];
    const otherData = domainData[otherKey] || { post_count: 0, "post_ratio(%)": 0 };

    // 数据准备
    let pieData = topDomains.map((item, index) => ({
        name: item.domain,
        value: item.post_count,
        ratio: item["post_ratio(%)"],
        isOther: false
    }));
    
    // 根据showOtherCategory决定是否添加"其他"
    if (showOtherCategory && otherData.post_count > 0) {
        pieData.push({
            name: "其他",
            value: otherData.post_count,
            ratio: otherData["post_ratio(%)"],
            isOther: true
        });
    }
    
    // 过滤无数据项
    pieData = pieData.filter(d => d.value > 0);
    
    // 如果不显示"其他"，重新计算占比（相对top-K的百分比）
    if (!showOtherCategory) {
        const topTotal = pieData.reduce((sum, d) => sum + d.value, 0);
        pieData.forEach(d => {
            d.ratio = (d.value / topTotal) * 100;
        });
    }
    
    // 2. 饼图尺寸
    const pieWidth = totalWidth * 0.4;
    const pieHeight = totalHeight * 0.8;
    const radius = Math.min(pieWidth, pieHeight) / 2 - 40;
    const centerX = totalWidth * (partyIndex * 0.5 + 0.25);
    const centerY = totalHeight / 2;

    console.log(`绘制${title}饼图，索引：${partyIndex}，中心：(${centerX}, ${centerY})，半径：${radius}`);

    // 3. 创建饼图容器（始终创建）
    const pieG = svg.append("g")
        .attr("class", "pie-single")
        .attr("transform", `translate(${centerX}, ${centerY})`);

    // 4. 标题
    pieG.append("text")
    .attr("class", "pie-title")
    .attr("x", 0)
    .attr("y", -radius - 30) 
    .attr("text-anchor", "middle")
    .attr("font-size", "20px")
    .attr("fill", "#2f2d2dff")
    .text(title);

    console.log(`标题位置：(${centerX}, ${-radius - 30})`);

    // === 无数据分支 ===
    if (pieData.length === 0) {
        pieG.append("text")
            .attr("class", "no-data")
            .attr("x", 0)
            .attr("y", 0)
            .attr("text-anchor", "middle")
            .attr("fill", "#999")
            .text("暂无数据");
        return;
    }

    // 5. 饼图生成器
    const pie = d3.pie()
        .value(d => d.value)
        .sort(null);
    const arc = d3.arc()
        .innerRadius(0)
        .outerRadius(radius);
    const outerArc = d3.arc()
        .innerRadius(radius + 15)
        .outerRadius(radius + 15);

    // 6. 绘制饼图扇区（带动画）
    const arcs = pieG.selectAll(".arc")
        .data(pie(pieData))
        .enter()
        .append("g")
        .attr("class", "arc pie-arc");

    // 7. 扇区路径
    arcs.append("path")
        .attr("fill", (d, i) => morandiColors[i % morandiColors.length])
        .style("stroke", "#fff")
        .style("stroke-width", "1px")
        .each(function(d) { this._current = d; })
        .transition()
        .duration(800)
        .attrTween("d", function(d) {
            const interpolate = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
            return function(t) {
                return arc(interpolate(t));
            };
        });

    // 8. 创建提示框
    const tooltip = d3.select("body").select(".pie-tooltip").empty()
        ? d3.select("body").append("div").attr("class", "pie-tooltip")
        : d3.select("body").select(".pie-tooltip");

    // 9. 交互事件
    arcs.on("mouseover", function(event, d) {
        // 高亮当前扇区，其他变暗
        arcs.classed("dim", true);
        d3.select(this).classed("dim", false);
        
        // 高亮对应文本
        pieG.selectAll(".pie-text").classed("highlight", false);
        d3.select(this).select(".pie-text").classed("highlight", true);
        
        // 显示提示框
        tooltip.transition().duration(200).style("opacity", 0.9);
        tooltip.html(`
            域名：${d.data.name}<br/>
            发帖数：${d.data.value}<br/>
            占比：${d.data.ratio.toFixed(2)}%
        `)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 20) + "px");
    })
    .on("mouseout", function() {
        // 恢复所有扇区
        arcs.classed("dim", false);
        pieG.selectAll(".pie-text").classed("highlight", false);
        tooltip.transition().duration(200).style("opacity", 0);
    })
    .on("click", function(event, d) {

        showArticlePanel();   // ← 新增这一行，饼图点击时：强制切回文本模式（非常重要）

        // 点击“其他”展开 Top-K
        if (d.data.isOther) {
            showOtherCategory = false;
            initDualPartyPieChart();
            return;
        }

        // === 加载对应 domain 的样例文章 ===
        const domain = d.data.name;
        console.log(`当前title: ${title}, 点击域名：${domain}，加载样例文章`);
        loadDomainArticles(domain, title);
    });
   

    // 10. 绘制文本标签（延迟出现）
    arcs.append("text")
        .attr("dy", ".35em")
        .attr("class", "pie-text")
        .style("opacity", 0)
        .attr("transform", function(d) {
            const pos = outerArc.centroid(d);
            pos[0] = centerX + (midAngle(d) < Math.PI ? 1 : -1) * (radius + 25);
            const angle = midAngle(d);
            const yOffset = Math.sin(angle) * 5;
            return `translate(${pos[0] - centerX}, ${pos[1] + yOffset})`;
        })
        .style("text-anchor", function(d) {
            return midAngle(d) < Math.PI ? "start" : "end";
        })
        .text(function(d) {
            const domain = d.data.name;
            return domain.length > 8 ? domain.substring(0, 8) + "..." : domain;
        })
        .transition()
        .delay(800)
        .duration(400)
        .style("opacity", 1);

    // 11. 绘制连接线（延迟出现）
    arcs.append("polyline")
        .style("opacity", 0)
        .attr("points", function(d) {
            const pos = outerArc.centroid(d);
            pos[0] = centerX + (midAngle(d) < Math.PI ? 1 : -1) * (radius + 15);
            return [arc.centroid(d), outerArc.centroid(d), [pos[0] - centerX, pos[1]]];
        })
        .style("fill", "none")
        .style("stroke", "#ccc")
        .style("stroke-width", "1px")
        .transition()
        .delay(800)
        .duration(400)
        .style("opacity", 1);
}

// 辅助函数：计算扇区中间角度
function midAngle(d) {
    return d.startAngle + (d.endAngle - d.startAngle) / 2;
}

// 辅助函数：获取数据类型名称
function getDataTypeName() {
    switch(currentDataType) {
        case 'post_count': return '发帖数';
        case 'total_upvotes': return '总点赞数';
        case 'total_comments': return '总评论数';
        default: return '发帖数';
    }
}


async function loadDomainArticles(domain, title) {
    try {
        const res = await fetch(`data/domain_data/${title}/${domain}.json`);
        console.log(`加载域名样例数据路径: ../data/domain_data/${title}/${domain}.json`);
        const records = await res.json();  

        currentDomainName = domain;
        currentArticleIndex = 0;

        // 取 articles 字段
        currentDomainArticles = records.map(r => r.articles);
        console.log(`加载到 ${currentDomainArticles.length} 篇样例文章`);
        renderArticlePanel();
    }
    catch (err) {
        console.error("加载 domain 样例失败:", err);
        document.getElementById("articleViewer").innerHTML =
            `<span style="color:#999">❌ 未找到样例文本</span>`;
    }
}

function renderArticlePanel() {
    if (!currentDomainArticles.length) return;

    const article = currentDomainArticles[currentArticleIndex];
    const viewer = document.getElementById("articleViewer");

    viewer.innerHTML = `
        <div style="font-size:16px;
                    color:#444; /* 调整文字颜色更柔和 */
                    margin-bottom:15px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif; /* 现代无衬线字体组合 */
                    font-weight: 500;">
            domain：<b>${currentDomainName}</b>
        </div>

        <div style="height:500px;
                    overflow-y:auto;
                    border:1px solid #e5e7eb; /* 更细腻的边框色 */
                    padding:20px; /* 增加内边距更舒适 */
                    line-height:1.85; /* 微调行高提升可读性 */
                    font-size:15px; /* 适度放大正文 */
                    color:#333; /* 正文颜色更清晰 */
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; /* 适配中英文的字体组合 */
                    letter-spacing: 0.5px; /* 增加少量字间距，提升易读性 */
                    background-color: #fafafa; /* 浅背景色减少视觉疲劳 */
                    border-radius: 8px; /* 圆角更美观 */">
            ${article}
        </div>

        <div style="margin-top:18px;display:flex;justify-content:flex-end;gap:12px;">
            <button id="nextArticleBtn"
                style="padding:8px 18px;
                       border:none; /* 去掉边框，优化按钮样式 */
                       background:#409eff;
                       color:#fff;
                       border-radius:6px; /* 更大的圆角 */
                       cursor:pointer;
                       font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; /* 按钮字体统一 */
                       font-size:14px;
                       font-weight: 500;
                       transition: background-color 0.2s ease; /*  hover 过渡效果 */">
                下一篇 →
            </button>
        </div>
    `;

    // 为按钮添加hover效果
    const nextBtn = document.getElementById("nextArticleBtn");
    nextBtn.onclick = () => {
        currentArticleIndex = (currentArticleIndex + 1) % currentDomainArticles.length;
        renderArticlePanel();
    };
    nextBtn.onmouseover = () => {
        nextBtn.style.backgroundColor = "#66b1ff";
    };
    nextBtn.onmouseout = () => {
        nextBtn.style.backgroundColor = "#409eff";
    };
}
// 窗口大小自适应
window.addEventListener("resize", function() {
    if (currentChartType === "trend") {
        initTimeChart();
    } else {
        initDualPartyPieChart();
    }
});