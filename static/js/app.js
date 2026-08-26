/**
 * 16型动物版MBTI性格测试 - 前端交互逻辑
 *
 * 职责:
 *   - 管理首页 / 测试页 / 结果页三个屏幕的切换
 *   - 调用后端 API 获取题目并逐题展示
 *   - 记录作答、提交计分、渲染结果
 *   - 处理结果页刷新等边界情况
 */
(function () {
    "use strict";

    // ---------- DOM 元素引用 ----------
    const homeScreen = document.getElementById("home-screen");
    const testScreen = document.getElementById("test-screen");
    const resultScreen = document.getElementById("result-screen");
    const btnStart = document.getElementById("btn-start");
    const btnRestart = document.getElementById("btn-restart");
    const currentQEl = document.getElementById("current-q");
    const totalQEl = document.getElementById("total-q");
    const progressFill = document.getElementById("progress-fill");
    const dimensionTag = document.getElementById("dimension-tag");
    const questionText = document.getElementById("question-text");
    const optionsList = document.getElementById("options-list");
    const resultLoading = document.getElementById("result-loading");
    const resultContent = document.getElementById("result-content");

    // ---------- 状态 ----------
    /** @type {Array} 题目列表 */
    let questions = [];
    /** @type {number} 当前题目索引(0-based) */
    let currentIndex = 0;
    /** @type {Array} 用户作答记录 */
    let answers = [];
    /** @type {boolean} 是否正在提交结果 */
    let submitting = false;

    // ---------- 维度中文名映射 ----------
    const DIM_NAMES = {
        "EI": { left: "外向 E", right: "内向 I" },
        "SN": { left: "感觉 S", right: "直觉 N" },
        "TF": { left: "思考 T", right: "情感 F" },
        "JP": { left: "判断 J", right: "知觉 P" }
    };

    // ---------- 屏幕切换 ----------
    function showScreen(screen) {
        // 隐藏所有屏幕,显示目标屏幕
        document.querySelectorAll(".screen").forEach(function (el) {
            el.classList.remove("active");
        });
        screen.classList.add("active");
        // 回到顶部
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // ---------- 启动测试 ----------
    async function startTest() {
        // 重置状态
        currentIndex = 0;
        answers = [];
        submitting = false;
        resultLoading.style.display = "block";
        resultContent.style.display = "none";

        // 若题库未加载,则请求后端
        if (questions.length === 0) {
            try {
                const res = await fetch("/api/questions");
                const json = await res.json();
                if (json.code !== 0) {
                    throw new Error(json.message || "题目加载失败");
                }
                questions = json.data.questions;
                totalQEl.textContent = json.data.total;
            } catch (err) {
                alert("题目加载失败,请稍后重试:" + err.message);
                return;
            }
        }

        // 渲染第一题
        renderQuestion();
        showScreen(testScreen);
    }

    // ---------- 渲染当前题目 ----------
    function renderQuestion() {
        const q = questions[currentIndex];
        const total = questions.length;

        // 更新进度
        currentQEl.textContent = "第 " + (currentIndex + 1) + " 题";
        const percent = ((currentIndex) / total) * 100;
        progressFill.style.width = percent + "%";

        // 维度标签
        const dimName = (DIM_NAMES[q.dimension] || {}).left || q.dimension;
        dimensionTag.textContent = q.dimension + " 维度";

        // 题干
        questionText.textContent = q.text;

        // 选项
        optionsList.innerHTML = "";
        q.options.forEach(function (opt) {
            const item = document.createElement("button");
            item.className = "option-item";
            item.innerHTML =
                '<span class="option-key">' + opt.key + "</span>" +
                '<span class="option-text">' + opt.text + "</span>";
            // 选择选项后自动进入下一题
            item.addEventListener("click", function () {
                selectOption(opt.key);
            });
            optionsList.appendChild(item);
        });
    }

    // ---------- 选择选项 ----------
    function selectOption(optionKey) {
        const q = questions[currentIndex];
        // 记录作答
        answers.push({
            questionIndex: q.index,
            optionKey: optionKey
        });

        // 进入下一题或提交结果
        currentIndex++;
        if (currentIndex < questions.length) {
            renderQuestion();
        } else {
            // 全部完成,提交结果
            submitAnswers();
        }
    }

    // ---------- 提交答案并获取结果 ----------
    async function submitAnswers() {
        if (submitting) return;
        submitting = true;

        // 显示加载中
        showScreen(resultScreen);
        resultLoading.style.display = "block";
        resultContent.style.display = "none";

        // 标记当前在结果页,用于刷新检测
        sessionStorage.setItem("mbti_result_entered", "1");

        try {
            const res = await fetch("/api/result", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ answers: answers })
            });
            const json = await res.json();
            if (json.code !== 0) {
                throw new Error(json.message || "结果生成失败");
            }
            renderResult(json.data);
        } catch (err) {
            alert("结果生成失败:" + err.message + "\n请返回首页重新测试。");
            sessionStorage.removeItem("mbti_result_entered");
            showScreen(homeScreen);
        } finally {
            submitting = false;
        }
    }

    // ---------- 渲染结果 ----------
    function renderResult(data) {
        // 动物与类型
        document.getElementById("result-emoji").textContent = data.emoji;
        document.getElementById("result-animal-label").textContent = data.animal;
        document.getElementById("result-type").textContent = data.mbtiType;
        document.getElementById("result-nickname").textContent = data.nickname;
        document.getElementById("result-traits").textContent = data.traits;

        // 维度占比条
        const barsWrap = document.getElementById("dimension-bars");
        barsWrap.innerHTML = "";
        ["EI", "SN", "TF", "JP"].forEach(function (dim) {
            const d = data.dimensions[dim];
            if (!d) return;
            const names = DIM_NAMES[dim];
            const bar = document.createElement("div");
            bar.className = "dim-bar";
            bar.innerHTML =
                '<div class="dim-bar-label">' +
                '<span class="dim-letter">' + names.left + " " + d.left.percent + "%</span>" +
                '<span class="dim-letter">' + names.right + " " + d.right.percent + "%</span>" +
                "</div>" +
                '<div class="dim-bar-track">' +
                '<div class="dim-bar-fill-left" style="width:' + d.left.percent + '%"></div>' +
                '<div class="dim-bar-fill-right" style="width:' + d.right.percent + '%"></div>' +
                "</div>";
            barsWrap.appendChild(bar);
        });

        // 优势
        const strengthsEl = document.getElementById("result-strengths");
        strengthsEl.innerHTML = "";
        data.strengths.forEach(function (s) {
            const li = document.createElement("li");
            li.textContent = s;
            strengthsEl.appendChild(li);
        });

        // 劣势
        const weaknessesEl = document.getElementById("result-weaknesses");
        weaknessesEl.innerHTML = "";
        data.weaknesses.forEach(function (w) {
            const li = document.createElement("li");
            li.textContent = w;
            weaknessesEl.appendChild(li);
        });

        // 适合方向
        const careersEl = document.getElementById("result-careers");
        careersEl.innerHTML = "";
        data.careers.forEach(function (c) {
            const tag = document.createElement("span");
            tag.className = "career-tag";
            tag.textContent = c;
            careersEl.appendChild(tag);
        });

        // 切换显示
        resultLoading.style.display = "none";
        resultContent.style.display = "block";
    }

    // ---------- 重新测试 ----------
    function restart() {
        sessionStorage.removeItem("mbti_result_entered");
        answers = [];
        currentIndex = 0;
        submitting = false;
        showScreen(homeScreen);
    }

    // ---------- 事件绑定 ----------
    btnStart.addEventListener("click", startTest);
    btnRestart.addEventListener("click", restart);

    // ---------- 结果页刷新处理 ----------
    // 需求:用户在结果页面刷新时,结果不保存,提示返回首页重新测试
    window.addEventListener("load", function () {
        if (sessionStorage.getItem("mbti_result_entered") === "1") {
            // 清除标记,提示用户
            sessionStorage.removeItem("mbti_result_entered");
            // 确保停留在首页
            showScreen(homeScreen);
            setTimeout(function () {
                alert("测试结果不保存,请重新开始测试吧~");
            }, 100);
        }
    });
})();
