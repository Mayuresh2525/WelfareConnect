// ============================================================
// WELFARECONNECT - SCRIPT.JS
// ============================================================


// ============================================================
// GLOBAL STATE
// ============================================================

let stage = "general";

let currentQuiz = 0;
let quizScore = 0;
let quizAnswered = false;


// ============================================================
// QUIZ DATA
// ============================================================

const quizzes = [

    {
        q: "What is the best first step before applying for a welfare scheme?",

        o: [
            "Send money to an agent",
            "Check the official eligibility and scheme information",
            "Share your OTP",
            "Use any website found in a search"
        ],

        a: 1,

        e: "Always verify current eligibility and application information through an official source."
    },

    {
        q: "Where should you normally continue for the actual application?",

        o: [
            "A random social-media page",
            "An unofficial blog",
            "The official government portal",
            "A forwarded message"
        ],

        a: 2,

        e: "Welfare Connect is a guide. The actual application should be completed through the relevant official channel."
    },

    {
        q: "Why is a document checklist useful?",

        o: [
            "It guarantees approval",
            "It helps users prepare required documents",
            "It replaces the government portal",
            "It changes eligibility rules"
        ],

        a: 1,

        e: "A checklist helps users prepare before starting an application."
    },

    {
        q: "What does an eligibility guide provide?",

        o: [
            "A guaranteed approval",
            "An estimate based on available criteria",
            "A government decision",
            "A replacement for official verification"
        ],

        a: 1,

        e: "A guide can help users understand basic criteria, but the official authority decides eligibility."
    },

    {
        q: "What should you do if scheme information appears outdated?",

        o: [
            "Use it anyway",
            "Verify the current information on the official portal",
            "Share it immediately",
            "Guess the missing details"
        ],

        a: 1,

        e: "Government scheme rules can change, so verify current details on the official source."
    }

];


// ============================================================
// SURVEY QUESTIONS (CONTINUOUS 1-10)
// ============================================================

const surveyQs = [

    "How familiar are you with central and state government welfare schemes?",

    "In general, how easy or difficult is it to find clear information about government schemes?",

    "How confident are you in understanding eligibility rules and requirements for welfare schemes?",

    "How confident are you in knowing what documents are typically needed when applying for a scheme?",

    "How clear are you about where to start when applying for a government scheme?",

    "How confident are you in identifying the genuine, official government portal for a scheme?",

    "How helpful was the Welfare Connect platform in discovering schemes relevant to your profile?",

    "How useful did you find the interactive document checklist and step-by-step application guide?",

    "How easy was it to navigate and use the Welfare Connect website?",

    "How likely are you to use Welfare Connect in the future or recommend it to others seeking scheme information?"

];


// ============================================================
// SURVEY OPTIONS
// ============================================================

const surveyOptions = [

    [
        "Not familiar at all",
        "Slightly familiar",
        "Moderately familiar",
        "Very familiar",
        "Extremely familiar"
    ],

    [
        "Very difficult",
        "Difficult",
        "Neutral",
        "Easy",
        "Very easy"
    ],

    [
        "Not confident at all",
        "Slightly confident",
        "Moderately confident",
        "Very confident",
        "Extremely confident"
    ],

    [
        "Not confident at all",
        "Slightly confident",
        "Moderately confident",
        "Very confident",
        "Extremely confident"
    ],

    [
        "Not clear at all",
        "Slightly clear",
        "Moderately clear",
        "Very clear",
        "Extremely clear"
    ],

    [
        "Not confident at all",
        "Slightly confident",
        "Moderately confident",
        "Very confident",
        "Extremely confident"
    ],

    [
        "Not helpful at all",
        "Slightly helpful",
        "Moderately helpful",
        "Very helpful",
        "Extremely helpful"
    ],

    [
        "Not useful at all",
        "Slightly useful",
        "Moderately useful",
        "Very useful",
        "Extremely useful"
    ],

    [
        "Very difficult",
        "Difficult",
        "Neutral",
        "Easy",
        "Very easy"
    ],

    [
        "Very unlikely",
        "Unlikely",
        "Neutral",
        "Likely",
        "Very likely"
    ]

];


// ============================================================
// ANONYMOUS ANALYTICS / ACTIVITY TRACKING
// ============================================================

const VISITOR_ID_KEY = "welfareconnect_visitor_id";

function getVisitorId() {

    let visitorId =
        localStorage.getItem(
            VISITOR_ID_KEY
        );


    if (!visitorId) {

        if (
            window.crypto &&
            crypto.randomUUID
        ) {

            visitorId =
                crypto.randomUUID();

        } else {

            visitorId =
                "visitor-" +
                Date.now() +
                "-" +
                Math.random()
                    .toString(36)
                    .slice(2, 10);

        }


        localStorage.setItem(
            VISITOR_ID_KEY,
            visitorId
        );

    }


    return visitorId;

}


function trackActivity(
    eventType,
    data = {}
) {

    const payload = {

        visitor_id:
            getVisitorId(),

        event_type:
            eventType,

        ...data

    };


    if (
        eventType ===
            "official_link_click" &&
        navigator.sendBeacon
    ) {

        try {

            const blob =
                new Blob(
                    [
                        JSON.stringify(
                            payload
                        )
                    ],
                    {
                        type:
                            "application/json"
                    }
                );


            navigator.sendBeacon(
                "/api/track",
                blob
            );

            return;

        } catch (error) {

            console.warn(
                "Analytics beacon failed:",
                error
            );

        }

    }


    fetch(
        "/api/track",
        {

            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body:
                JSON.stringify(
                    payload
                ),

            keepalive: true

        }
    ).catch(error => {

        console.warn(
            "Analytics tracking failed:",
            error
        );

    });

}


function trackPageView() {

    trackActivity(
        "page_view"
    );

}


// ============================================================
// NAVIGATION
// ============================================================

function toggleNav() {

    const nav =
        document.getElementById(
            "nav"
        );


    if (nav) {

        nav.classList.toggle(
            "open"
        );

    }

}


// ============================================================
// LOAD SCHEMES
// ============================================================

async function loadSchemes() {

    const searchElement =
        document.getElementById(
            "search"
        );


    const categoryElement =
        document.getElementById(
            "category"
        );


    const audienceElement =
        document.getElementById(
            "audience"
        );


    const resultsElement =
        document.getElementById(
            "results"
        );


    if (
        !searchElement ||
        !categoryElement ||
        !audienceElement ||
        !resultsElement
    ) {

        return;

    }


    const q =
        searchElement.value;


    const category =
        categoryElement.value;


    const audience =
        audienceElement.value;


    const filterSignature =
        JSON.stringify({
            q,
            category,
            audience
        });


    if (
        window._lastTrackedFilter !==
        filterSignature
    ) {

        window._lastTrackedFilter =
            filterSignature;


        if (q.trim()) {

            trackActivity(
                "search",
                {
                    query_text:
                        q.trim()
                }
            );

        }


        if (
            category ||
            audience
        ) {

            trackActivity(
                "filter",
                {
                    details:
                        JSON.stringify({
                            category,
                            audience
                        })
                }
            );

        }

    }


    try {

        const response =
            await fetch(
                `/api/schemes?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}&audience=${encodeURIComponent(audience)}`
            );


        const data =
            await response.json();


        resultsElement.innerHTML =
            data.length

            ?

            data.map(
                s => `

                <article class="card">

                    <span class="tag">
                        ${s.category}
                    </span>


                    <h3>
                        ${s.name}
                    </h3>


                    <span class="category-pill">
                        ${s.audience}
                    </span>


                    <p>
                        ${s.summary}
                    </p>


                    <div class="card-actions">

                        <button
                            class="link-btn"
                            onclick="openScheme(${s.id})"
                        >
                            View Full Guide →
                        </button>

                    </div>

                </article>

            `
            ).join("")

            :

            `
                <div
                    class="box"
                    style="padding:25px"
                >

                    <b>
                        No matching schemes.
                    </b>


                    <p>
                        Try another category,
                        audience or keyword.
                    </p>

                </div>
            `;


    } catch (error) {

        console.error(
            "Could not load schemes:",
            error
        );

    }

}


// ============================================================
// OPEN SCHEME
// ============================================================

async function openScheme(id) {

    try {

        const response =
            await fetch(
                `/api/scheme/${id}`
            );


        const s =
            await response.json();


        if (s.error) {

            return;

        }


        trackActivity(
            "scheme_view",
            {
                scheme_id: Number(id)
            }
        );


        document.getElementById(
            "modalBody"
        ).innerHTML = `

            <span class="tag">
                ${s.category} • ${s.audience}
            </span>


            <h2>
                ${s.name}
            </h2>


            <p>
                ${s.summary}
            </p>


            <h3>
                Basic eligibility
            </h3>


            <p>
                ${s.eligibility}
            </p>


            <h3>
                Benefits
            </h3>


            <p>
                ${s.benefits}
            </p>


            <h3>
                Document checklist
            </h3>


            <ul class="checklist">

                ${s.documents.map(
                    (document, index) => `

                        <li>

                            <label>

                                <input
                                    type="checkbox"
                                >

                                ${document}

                            </label>

                        </li>

                    `
                ).join("")}

            </ul>


            <h3>
                Application guide
            </h3>


            <ol>

                ${s.steps.map(
                    step => `

                        <li>
                            ${step}
                        </li>

                    `
                ).join("")}

            </ol>


            <div class="official">

                <a
                    class="btn primary"
                    href="${s.official}"
                    target="_blank"
                    rel="noopener"
                    onclick="trackActivity('official_link_click', {scheme_id: ${Number(s.id)}})"
                >
                    Open Official Portal ↗
                </a>

            </div>


            <p class="note">

                Educational guide only.
                Verify current eligibility, benefits,
                documents and procedures on the official portal.

            </p>

        `;


        document
            .getElementById("modal")
            .classList.remove("hidden");


    } catch (error) {

        console.error(
            "Could not open scheme:",
            error
        );

    }

}


// ============================================================
// CLOSE SCHEME MODAL
// ============================================================

function closeModal(e) {

    if (
        !e ||
        e.target.id === "modal"
    ) {

        document
            .getElementById("modal")
            .classList.add("hidden");

    }

}


// ============================================================
// QUIZ
// ============================================================

function renderQuiz() {

    const quizElement =
        document.getElementById("quiz");

    const nextButton =
        document.getElementById("quizNext");


    if (!quizElement || !nextButton) {

        return;

    }


    const question =
        quizzes[currentQuiz];


    quizElement.innerHTML = `

        <div class="quiz-progress">

            QUESTION
            ${currentQuiz + 1}
            OF
            ${quizzes.length}

        </div>


        <h3>
            ${question.q}
        </h3>


        ${
            question.o.map(
                (option, index) => `

                    <button
                        class="quiz-option"
                        onclick="answerQuiz(${index}, this)"
                    >
                        ${option}
                    </button>

                `
            ).join("")
        }

    `;


    nextButton.style.display =
        "none";

}


function answerQuiz(index, button) {

    if (quizAnswered) {

        return;

    }


    quizAnswered = true;


    const question =
        quizzes[currentQuiz];


    document
        .querySelectorAll(
            ".quiz-option"
        )
        .forEach(
            element => {

                element.disabled = true;

            }
        );


    if (index === question.a) {

        quizScore++;


        button.classList.add(
            "correct"
        );


    } else {

        button.classList.add(
            "wrong"
        );


        document
            .querySelectorAll(
                ".quiz-option"
            )[question.a]
            .classList.add(
                "correct"
            );

    }


    document
        .getElementById("quiz")
        .insertAdjacentHTML(
            "beforeend",
            `

                <div class="quiz-feedback">

                    <b>
                        ${
                            index === question.a
                            ? "Correct! ✅"
                            : "Not quite. ❌"
                        }
                    </b>

                    <br>

                    ${question.e}

                </div>

            `
        );


    const nextButton =
        document.getElementById(
            "quizNext"
        );


    nextButton.style.display =
        "inline-block";


    nextButton.textContent =
        currentQuiz === quizzes.length - 1
        ? "Show Result"
        : "Next Question";

}


function nextQuiz() {

    if (!quizAnswered) {

        return;

    }


    if (
        currentQuiz <
        quizzes.length - 1
    ) {

        currentQuiz++;

        quizAnswered = false;

        renderQuiz();

        return;

    }


    trackActivity(
        "quiz_completed",
        {
            score: quizScore,
            total: quizzes.length
        }
    );


    document.getElementById(
        "quiz"
    ).innerHTML = `

        <div class="quiz-feedback">

            <h2>
                Your score:
                ${quizScore}/${quizzes.length}
            </h2>

            <p>
                ${
                    quizScore >= 4
                    ? "Excellent awareness! 🎉"
                    : "Good start — review the guides and try again."
                }
            </p>

        </div>

    `;


    const nextButton =
        document.getElementById(
            "quizNext"
        );


    nextButton.textContent =
        "Try Again";


    nextButton.style.display =
        "inline-block";


    nextButton.onclick =
        restartQuiz;

}


function restartQuiz() {

    currentQuiz = 0;

    quizScore = 0;

    quizAnswered = false;


    const nextButton =
        document.getElementById(
            "quizNext"
        );


    nextButton.onclick =
        nextQuiz;


    renderQuiz();

}


// ============================================================
// RESET SURVEY FORM
// ============================================================

function resetSurvey() {

    const nameInput =
        document.getElementById(
            "surveyName"
        );

    const statusSelect =
        document.getElementById(
            "surveyStatus"
        );

    const genderSelect =
        document.getElementById(
            "surveyGender"
        );

    const ageSelect =
        document.getElementById(
            "surveyAge"
        );


    if (nameInput) {

        nameInput.value = "";

    }


    if (statusSelect) {

        statusSelect.value = "";

    }


    if (genderSelect) {

        genderSelect.value = "";

    }


    if (ageSelect) {

        ageSelect.value = "";

    }


    document
        .querySelectorAll(
            "#surveyQs .opt.sel"
        )
        .forEach(
            button => {

                button.classList.remove(
                    "sel"
                );

            }
        );

}


// ============================================================
// BUILD PARTICIPANT DETAILS
// ============================================================

function buildParticipantDetails() {

    const surveyBox =
        document.getElementById(
            "surveyQs"
        );


    if (!surveyBox) {

        return;

    }


    if (
        document.getElementById(
            "participantDetails"
        )
    ) {

        return;

    }


    const details =
        document.createElement(
            "div"
        );


    details.id =
        "participantDetails";


    details.innerHTML = `

        <div
            class="box"
            style="margin-bottom:20px;"
        >

            <h3>
                Participant Details
            </h3>


            <p class="note">
                Please complete all details
                before submitting the survey.
            </p>


            <div style="margin-top:15px;">

                <label
                    for="surveyName"
                    style="display:block;margin-bottom:6px;font-weight:600;"
                >
                    Name
                </label>


                <input
                    type="text"
                    id="surveyName"
                    placeholder="Enter your name"
                    required
                    style="width:100%;padding:12px;border:1px solid #ccc;border-radius:8px;"
                >

            </div>


            <div style="margin-top:15px;">

                <label
                    for="surveyStatus"
                    style="display:block;margin-bottom:6px;font-weight:600;"
                >
                    Current Status
                </label>


                <select
                    id="surveyStatus"
                    required
                    style="width:100%;padding:12px;border:1px solid #ccc;border-radius:8px;"
                >

                    <option value="">
                        Select your status
                    </option>

                    <option value="Student">
                        Student
                    </option>

                    <option value="Working Professional">
                        Working Professional
                    </option>

                    <option value="Self-Employed / Business">
                        Self-Employed / Business
                    </option>

                    <option value="Unemployed">
                        Unemployed
                    </option>

                    <option value="Homemaker">
                        Homemaker
                    </option>

                    <option value="Other">
                        Other
                    </option>

                </select>

            </div>


            <div style="margin-top:15px;">

                <label
                    for="surveyGender"
                    style="display:block;margin-bottom:6px;font-weight:600;"
                >
                    Gender
                </label>


                <select
                    id="surveyGender"
                    required
                    style="width:100%;padding:12px;border:1px solid #ccc;border-radius:8px;"
                >

                    <option value="">
                        Select your gender
                    </option>

                    <option value="Male">
                        Male
                    </option>

                    <option value="Female">
                        Female
                    </option>

                    <option value="Other">
                        Other
                    </option>

                </select>

            </div>


            <div style="margin-top:15px;">

                <label
                    for="surveyAge"
                    style="display:block;margin-bottom:6px;font-weight:600;"
                >
                    Age Group
                </label>


                <select
                    id="surveyAge"
                    required
                    style="width:100%;padding:12px;border:1px solid #ccc;border-radius:8px;"
                >

                    <option value="">
                        Select your age group
                    </option>

                    <option value="Under 18">
                        Under 18
                    </option>

                    <option value="18–25">
                        18–25
                    </option>

                    <option value="26–35">
                        26–35
                    </option>

                    <option value="36–50">
                        36–50
                    </option>

                    <option value="Above 50">
                        Above 50
                    </option>

                </select>

            </div>

        </div>

    `;


    surveyBox.parentNode.insertBefore(
        details,
        surveyBox
    );

}


// ============================================================
// BUILD SURVEY QUESTIONS
// ============================================================

function buildSurvey() {

    const box =
        document.getElementById(
            "surveyQs"
        );


    if (!box) {

        return;

    }


    box.innerHTML =
        surveyQs.map(
            (question, index) => `

                <div class="q">

                    <p>
                        <b>
                            ${index + 1}.
                            ${question}
                        </b>
                    </p>


                    <div class="opts">

                        ${
                            surveyOptions[index]
                            .map(
                                (option, value) => `

                                    <button
                                        type="button"
                                        class="opt"
                                        data-i="${index}"
                                        data-v="${value + 1}"
                                        onclick="chooseSurvey(this)"
                                    >
                                        ${option}
                                    </button>

                                `
                            )
                            .join("")
                        }

                    </div>

                </div>

            `
        )
        .join("");

}


// ============================================================
// CHOOSE SURVEY ANSWER
// ============================================================

function chooseSurvey(button) {

    const question =
        button.dataset.i;


    document
        .querySelectorAll(
            `.opt[data-i="${question}"]`
        )
        .forEach(
            option => {

                option.classList.remove(
                    "sel"
                );

            }
        );


    button.classList.add(
        "sel"
    );

}


// ============================================================
// SUBMIT SURVEY
// ============================================================

async function submitSurvey() {

    const name =
        document
            .getElementById(
                "surveyName"
            )
            .value
            .trim();


    const status =
        document
            .getElementById(
                "surveyStatus"
            )
            .value;


    const gender =
        document
            .getElementById(
                "surveyGender"
            )
            .value;


    const ageGroup =
        document
            .getElementById(
                "surveyAge"
            )
            .value;


    const message =
        document.getElementById(
            "surveyMsg"
        );


    // --------------------------------------------------------
    // VALIDATE PARTICIPANT DETAILS
    // --------------------------------------------------------

    if (!name) {

        message.innerHTML =
            '<div class="msg">Please enter your name.</div>';

        return;

    }


    if (!status) {

        message.innerHTML =
            '<div class="msg">Please select your current status.</div>';

        return;

    }


    if (!gender) {

        message.innerHTML =
            '<div class="msg">Please select your gender.</div>';

        return;

    }


    if (!ageGroup) {

        message.innerHTML =
            '<div class="msg">Please select your age group.</div>';

        return;

    }


    // --------------------------------------------------------
    // COLLECT ANSWERS
    // --------------------------------------------------------

    const answers = [];


    for (
        let i = 0;
        i < surveyQs.length;
        i++
    ) {

        const selected =
            document.querySelector(
                `.opt[data-i="${i}"].sel`
            );


        if (!selected) {

            message.innerHTML = `

                <div class="msg">

                    Please answer question
                    ${i + 1}.

                </div>

            `;

            return;

        }


        answers.push(
            Number(
                selected.dataset.v
            )
        );

    }


    // --------------------------------------------------------
    // CALCULATE SCORE
    // --------------------------------------------------------

    const total =
        answers.reduce(
            (sum, value) =>
                sum + value,
            0
        );


    const score =
        Math.round(
            (total / 50) * 100
        );


    // --------------------------------------------------------
    // PREVENT DOUBLE SUBMISSION
    // --------------------------------------------------------

    const submitButton =
        document.querySelector(
            '#survey button[onclick="submitSurvey()"]'
        );


    if (submitButton) {

        submitButton.disabled = true;

        submitButton.dataset.originalText =
            submitButton.textContent;

        submitButton.textContent =
            "Submitting...";

    }


    message.innerHTML = `

        <div class="msg">

            Submitting your response...

        </div>

    `;


    // --------------------------------------------------------
    // DATA FOR GOOGLE FORM
    // --------------------------------------------------------

    // Google Form uses 18-25 with a normal hyphen.
    // Welfare Connect currently uses 18–25 with an en dash.

    const googleAgeGroup =
        ageGroup.replace(
            "18–25",
            "18-25"
        );


    const googleFormData = {

    name: name,

    status:
        status.replace(
            "Self-Employed / Business",
            "Self -Employed/Business"
        ),

    gender: gender,

    age_group:
        ageGroup.replace(
            "18–25",
            "18-25"
        ),

    q1: surveyOptions[0][answers[0] - 1],

    q2: surveyOptions[1][answers[1] - 1],

    q3: surveyOptions[2][answers[2] - 1],

    q4: surveyOptions[3][answers[3] - 1],

    q5: surveyOptions[4][answers[4] - 1],

    q6: surveyOptions[5][answers[5] - 1],

    q7: surveyOptions[6][answers[6] - 1],

    q8: surveyOptions[7][answers[7] - 1],

    q9: surveyOptions[8][answers[8] - 1],

    q10: surveyOptions[9][answers[9] - 1]

};


    // --------------------------------------------------------
    // GOOGLE APPS SCRIPT URL
    // --------------------------------------------------------

    const GOOGLE_FORM_CONNECTOR =
        "https://script.google.com/macros/s/AKfycbxCXtLgERuKD9Vyfzv5nWi4wgpFZllqWzJcfU8MFstuN8q86-d-zljrAQRCQXxGvC98Ug/exec";


    // --------------------------------------------------------
    // SUBMIT TO BOTH SYSTEMS
    // --------------------------------------------------------

    try {

        // ----------------------------------------------------
        // 1. SAVE TO WELFARE CONNECT / SQLITE
        // ----------------------------------------------------

        const response =
            await fetch(
                "/api/survey",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            name:
                                name,

                            status:
                                status,

                            gender:
                                gender,

                            age_group:
                                ageGroup,

                            stage:
                                stage,

                            answers:
                                answers

                        })

                }
            );


        const result =
            await response.json();


        if (!result.ok) {

            throw new Error(
                result.error ||
                "Could not save response."
            );

        }


        // ----------------------------------------------------
        // 2. SEND TO GOOGLE FORM
        // ----------------------------------------------------

        const googleBody =
            new URLSearchParams();


        Object.entries(
            googleFormData
        ).forEach(
            ([key, value]) => {

                googleBody.append(
                    key,
                    value
                );

            }
        );


        // We intentionally use no-cors because
        // Google Apps Script does not expose normal
        // CORS response headers to the browser.

        await fetch(
            GOOGLE_FORM_CONNECTOR,
            {

                method:
                    "POST",

                mode:
                    "no-cors",

                headers: {

                    "Content-Type":
                        "application/x-www-form-urlencoded;charset=UTF-8"

                },

                body:
                    googleBody.toString()

            }
        );


        // ----------------------------------------------------
        // BOTH SUBMISSIONS INITIATED
        // ----------------------------------------------------

        message.innerHTML = `

            <div class="msg">

                <b>
                    Response submitted successfully.
                </b>

                <br>

                Awareness score:
                ${score}/100

            </div>

        `;


        updateStats();


        trackActivity(
            "survey_submitted",
            {
                stage:
                    stage,

                score:
                    score
            }
        );


        resetSurvey();


    } catch (error) {

        console.error(
            "Survey submission error:",
            error
        );


        message.innerHTML = `

            <div class="msg">

                ${
                    error.message ||
                    "Could not submit the response."
                }

                <br>

                Please try again.

            </div>

        `;

    } finally {

        if (submitButton) {

            submitButton.disabled = false;

            submitButton.textContent =
                submitButton.dataset.originalText ||
                "Submit";

        }

    }

}


    




// ============================================================
// UPDATE DASHBOARD STATISTICS
// ============================================================

function escapeDashboardText(value) {
    const div = document.createElement("div");
    div.textContent = String(value ?? "");
    return div.innerHTML;
}


function renderQuestionBars(values) {
    const container = document.getElementById("questionBars");
    if (!container) return;

    const shortLabels = [
        "Eligibility familiarity",
        "Official portal confidence",
        "Document checklist",
        "Application confidence",
        "Information barriers",
        "Single-platform importance",
        "Interactive feature helpfulness",
        "Website navigation",
        "Application guidance",
        "Future use likelihood"
    ];

    container.innerHTML = values.map((value, index) => `
        <div class="question-bar-row">
            <div class="question-label">
                <span>Q${index + 1}</span>
                ${escapeDashboardText(shortLabels[index])}
            </div>
            <div class="question-track">
                <div class="question-fill" style="width:${Math.max(0, Math.min(100, value))}%"></div>
            </div>
            <div class="question-value">${Number(value).toFixed(0)}%</div>
        </div>
    `).join("");
}


function renderRatingDistribution(items) {
    const donut = document.getElementById("ratingDonut");
    const legend = document.getElementById("ratingLegend");
    const totalEl = document.getElementById("ratingTotal");
    if (!donut || !legend || !totalEl) return;

    const labels = ["Very low", "Low", "Moderate", "High", "Very high"];
    const degrees = [0, 0, 0, 0, 0];
    const total = items.reduce((sum, item) => sum + Number(item.count || 0), 0);
    const colors = ["#dbe4ef", "#a9bdd7", "#7ea0c7", "#4f80b5", "#2563eb"];

    let current = 0;
    items.forEach((item, index) => {
        const share = total ? (Number(item.count || 0) / total) * 360 : 0;
        degrees[index] = share;
        current += share;
    });

    let cursor = 0;
    const stops = items.map((item, index) => {
        const next = cursor + degrees[index];
        const stop = `${colors[index]} ${cursor}deg ${next}deg`;
        cursor = next;
        return stop;
    });

    donut.style.background = total
        ? `conic-gradient(${stops.join(", ")})`
        : "conic-gradient(#dfe6ef 0deg 360deg)";

    totalEl.textContent = total.toLocaleString();
    legend.innerHTML = items.map((item, index) => `
        <div class="rating-item">
            <i class="rating-dot" style="background:${colors[index]}"></i>
            <span>${labels[index]}</span>
            <strong>${Number(item.count || 0).toLocaleString()}</strong>
        </div>
    `).join("");
}


function renderResponseLineChart(items) {
    const svg = document.getElementById("responseLineChart");
    if (!svg) return;

    const width = 760;
    const height = 280;
    const left = 42;
    const right = 18;
    const top = 22;
    const bottom = 48;
    const chartW = width - left - right;
    const chartH = height - top - bottom;
    const values = items.map(item => Number(item.responses || 0));
    const max = Math.max(1, ...values);
    const points = items.map((item, index) => {
        const x = items.length === 1 ? left + chartW / 2 : left + (index * chartW / (items.length - 1));
        const y = top + chartH - ((Number(item.responses || 0) / max) * chartH);
        return { x, y, value: Number(item.responses || 0), day: item.day };
    });

    const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
    const area = `${path} L ${points[points.length - 1].x.toFixed(1)} ${(top + chartH).toFixed(1)} L ${points[0].x.toFixed(1)} ${(top + chartH).toFixed(1)} Z`;

    const grid = [0, .25, .5, .75, 1].map(ratio => {
        const y = top + chartH - ratio * chartH;
        const label = Math.round(max * ratio);
        return `<line class="chart-grid-line" x1="${left}" y1="${y}" x2="${width-right}" y2="${y}" />
                <text class="chart-text" x="${left-10}" y="${y+4}" text-anchor="end">${label}</text>`;
    }).join("");

    const labels = points.map(p => {
        const label = p.day ? p.day.slice(5) : "";
        return `<text class="chart-text" x="${p.x}" y="${height-18}" text-anchor="middle">${escapeDashboardText(label)}</text>`;
    }).join("");

    const dots = points.map(p => `
        <circle class="chart-point" cx="${p.x}" cy="${p.y}" r="5"></circle>
        <text class="chart-number" x="${p.x}" y="${p.y-10}" text-anchor="middle">${p.value}</text>
    `).join("");

    svg.innerHTML = `${grid}<path class="chart-area" d="${area}"></path><path class="chart-line" d="${path}"></path>${dots}${labels}`;
}


function renderDashboardInsight(categories, questions) {
    const title = document.getElementById("dashboardInsightTitle");
    const text = document.getElementById("dashboardInsightText");
    if (!title || !text) return;

    const groups = [
        ["Awareness & Knowledge", Number(categories.awareness || 0)],
        ["Access & Preparation", Number(categories.preparation || 0)],
        ["Platform Experience", Number(categories.platform || 0)]
    ];
    const valid = groups.filter(item => item[1] > 0);

    if (!valid.length || !questions.some(value => Number(value) > 0)) {
        title.textContent = "Waiting for survey data";
        text.textContent = "Once responses are available, this section highlights the comparatively stronger and weaker survey areas.";
        return;
    }

    const highest = [...valid].sort((a, b) => b[1] - a[1])[0];
    const lowest = [...valid].sort((a, b) => a[1] - b[1])[0];
    title.textContent = `${highest[0]} is currently the strongest area`;
    text.textContent = `${highest[0]} averages ${highest[1].toFixed(0)}%, while ${lowest[0]} averages ${lowest[1].toFixed(0)}%. These figures reflect the aggregate responses collected through the survey.`;
}


async function updateStats() {
    try {
        const response = await fetch("/api/stats");
        const s = await response.json();

        const setText = (id, value) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        };

        setText("dashResponses", Number(s.responses || 0).toLocaleString());
        setText("dashAverage", `${Number(s.average || 0).toFixed(0)}%`);

        const categories = s.category_averages || {};
        setText("dashAwareness", `${Number(categories.awareness || 0).toFixed(0)}%`);
        setText("dashPlatform", `${Number(categories.platform || 0).toFixed(0)}%`);
        setText("catAwareness", `${Number(categories.awareness || 0).toFixed(0)}%`);
        setText("catPreparation", `${Number(categories.preparation || 0).toFixed(0)}%`);
        setText("catPlatform", `${Number(categories.platform || 0).toFixed(0)}%`);

        renderQuestionBars(s.question_averages || []);
        renderRatingDistribution(s.rating_distribution || []);
        renderResponseLineChart(s.daily_responses || []);
        renderDashboardInsight(categories, s.question_averages || []);

    } catch (error) {
        console.error("Could not update survey dashboard:", error);
    }
}


// ============================================================
// INITIALIZE EVERYTHING
// ============================================================

buildParticipantDetails();

trackPageView();

buildSurvey();

renderQuiz();

loadSchemes();

updateStats();