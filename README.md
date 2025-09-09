
# Prysm Backend

## Overview

Prysm Backend is a Python‑based news aggregation and personalization
service built on **Firebase Cloud Functions**. It powers the Prysm iOS
app by fetching the latest news and social posts, extracting trending
topics and subtopics, summarizing articles with generative AI,
generating audio briefings, and delivering personalized updates to
users. The entry‑point (`main.py`) registers HTTP endpoints for testing
the GNews API and other functionality using `https_fn` and scheduler
triggershttps://github.com/AdamZinebii/PrysmBackend/blob/main/main.py#L11-L42. It imports modules for AI
interaction, news aggregation, audio generation, database operations,
notifications, and schedulinghttps://github.com/AdamZinebii/PrysmBackend/blob/main/main.py#L11-L42.

## Features

-   **News aggregation with multi‑source fallback.** The project wraps
    several news APIs (GNews, NewsAPI and SerpAPI) to search or fetch
    top headlines. The `serpapi_google_news_search` function in
    `modules/news/serpapi.py` attempts GNews first and falls back to
    NewsAPI or SerpAPI as needed, standardizing article fields and
    summarizing long content. Reddit content can also be incorporated
    via the `get_articles_subtopics_user` helper, which fetches posts
    and comments for specific subredditshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/news/news_helper.py#L19-L88.

-   **Trending topics and subtopic extraction.** The
    `modules/content/topics.py` file contains mappings from subtopics to
    parent categories (e.g., AI → technology, Finance → business) and
    functions to fetch trending topics or convert legacy topics to GNews
    formathttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/content/topics.py#L14-L34. It also provides heuristics to
    map user‑entered subtopics to queries and associated
    subredditshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/content/topics.py#L116-L145.

-   **AI‑powered summarization and conversation.** The
    `modules/ai/client.py` module wraps the OpenAI API. It builds system
    prompts tailored to a user's selected subjects and generates concise
    summaries, pickup lines, or interactive responses via GPT models.
    For example, the `generate_ai_response` helper constructs a
    conversation history and invokes the OpenAI chat
    endpointhttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/ai/client.py#L36-L75. The AI is also used to analyze
    conversations and update user preferences.

-   **Audio generation and podcast creation.** The backend integrates
    with multiple text‑to‑speech providers. ElevenLabs and Cartesia can
    convert generated content into speech; the
    `generate_text_to_speech_cartesia` function sends a request to the
    Cartesia API and returns WAV audio byteshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/audio/cartesia.py#L16-L28.
    Higher‑level functions in `modules/content/podcast.py` generate
    media‑twin scripts and assemble short podcasts, storing the
    resulting audio in Firebase Storage.

-   **Scheduled updates and notifications.** A scheduler function
    triggers periodic updates for each user. The `update` pipeline in
    `modules/scheduling/tasks.py` chains four operations: refreshing
    articles, generating a complete report, creating a simple podcast,
    and sending a push notificationhttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/scheduling/tasks.py#L24-L31. When
    run, it logs progress, stores reports, generates audio, and uses
    Firebase Cloud Messaging to notify the user of new
    contenthttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/scheduling/tasks.py#L44-L89.

-   **User preferences and database operations.** User topics, subtopics
    and detail level are stored in Firestore. The
    `modules/database/operations.py` module validates preference
    structures, saves them with timestamps, and supports updating
    specific subjectshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/database/operations.py#L13-L35. It also retrieves
    stored preferences and articles for report generation.

-   **Push notifications.** Using Firebase Cloud Messaging, the backend
    sends notifications to users when fresh updates are available. The
    `send_push_notification` function builds a message with Android and
    APNS configurations and gracefully handles common errors such as
    unregistered tokenshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/notifications/push.py#L57-L103.

-   **Interactive tests.** The
    `modules/content/simple_interactive_test.py` module demonstrates an
    interactive podcast session where a sample news script is narrated
    and the user can interrupt with questions. It generates audio on
    demand and responds either with pre‑written answers or by calling
    the OpenAI API for complex querieshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/content/simple_interactive_test.py#L30-L124.

## Project Structure

    ├── main.py                # Firebase Cloud Functions entry‑point and HTTP endpoints
    ├── requirements.txt       # Python dependencieshttps://github.com/AdamZinebii/PrysmBackend/blob/main/requirements.txt#L1-L13
    ├── modules/
    │   ├── ai/                # OpenAI client wrapper and conversation toolshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/ai/client.py#L36-L75
    │   ├── audio/             # Text‑to‑speech integrations (Cartesia, ElevenLabs)https://github.com/AdamZinebii/PrysmBackend/blob/main/modules/audio/cartesia.py#L16-L28
    │   ├── content/           # Generation helpers (pickup lines, topic summaries), topics mapping, podcasts
    │   ├── database/          # Firestore operations for saving/retrieving user preferences and articleshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/database/operations.py#L13-L35
    │   ├── news/              # Wrappers around GNews, NewsAPI, SerpAPI and Reddithttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/news/news_helper.py#L19-L88
    │   ├── notifications/     # Push notification helpershttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/notifications/push.py#L57-L103
    │   └── scheduling/        # Scheduled tasks for refreshing feeds, generating reports and podcastshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/scheduling/tasks.py#L24-L31
    └── modules/config.py      # API keys and configuration valueshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/config.py#L10-L16

## Requirements

Prysm Backend requires Python 3.9 or later. All Python dependencies are
defined in **requirements.txt**. Key packages include Firebase Cloud
Functions, Firebase Admin SDK, OpenAI, feedparser, requests and
othershttps://github.com/AdamZinebii/PrysmBackend/blob/main/requirements.txt#L1-L13. A Firebase project with Firestore and
Cloud Functions enabled is also required.

## Installation

1.  **Clone the repository:**

    ``` bash
    git clone https://github.com/AdamZinebii/PrysmBackend.git
    cd PrysmBackend
    ```

2.  **Create a virtual environment (optional but recommended):**

    ``` bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ``` bash
    pip install -r requirements.txt
    ```

4.  **Configure API keys and environment variables.** Many APIs require
    keys. Create a `.env` file (or set environment variables) with the
    following keys:

    -   `OPENAI_API_KEY` -- OpenAI API key (for GPT‑4 and text
        summarization).
    -   `SERPAPI_API_KEY` -- SerpAPI key.
    -   `GNEWS_API_KEY` -- GNews API key.
    -   `NEWSAPI_API_KEY` -- NewsAPI key.
    -   `ELEVENLABS_API_KEY` -- ElevenLabs Text‑to‑Speech key.
    -   `CARTESIA_API_KEY` -- Cartesia Text‑to‑Speech key. When unset,
        the code falls back to hard‑coded test keys defined in
        `modules/config.py`https://github.com/AdamZinebii/PrysmBackend/blob/main/modules/config.py#L10-L16, but you should
        provide your own keys for production.

5.  **Initialize Firebase.** Deploying requires a Firebase project with
    Firestore and Cloud Messaging enabled. Install the Firebase CLI and
    run:

    ``` bash
    firebase login
    firebase init functions
    ```

    Provide a service account JSON or set
    `GOOGLE_APPLICATION_CREDENTIALS` to point to your credentials.

## Running Locally

You can run Cloud Functions locally using the [Functions
Framework](https://github.com/GoogleCloudPlatform/functions-framework-python).
Install it and run the desired function target:

``` bash
pip install functions-framework
functions-framework --target=test_gnews_api --debug
```

This starts a local HTTP server exposing the `test_gnews_api` endpoint
defined in `main.py`. Similarly, you can run other functions for
testing. For tasks that depend on Firebase services, ensure that the
Firebase emulators are running or use a test Firebase project.

## Deployment

Deploying the backend to Firebase is straightforward once your project
and credentials are set up:

``` bash
firebase deploy --only functions
```

This command uploads the Cloud Functions defined in `main.py` to your
Firebase project. Ensure that Firestore and Cloud Messaging are enabled
and that the service account has permissions for reading/writing
Firestore and sending push notifications.

## Usage

-   **Testing the GNews API:** Send a GET request to the
    `test_gnews_api` endpoint. This function accepts `endpoint`,
    `query`, `category`, `lang`, `country` and `max` parameters and
    returns formatted articleshttps://github.com/AdamZinebii/PrysmBackend/blob/main/main.py#L51-L124.
-   **Fetching news:** Use the `fetch_news_with_gnews` endpoint to fetch
    news articles for a topic or query. It supports both GET and POST
    and returns a list of articles with metadata.
-   **Updating a user feed:** The scheduler can trigger the `update`
    pipeline, which refreshes articles, creates a report, generates a
    podcast and sends a push notificationhttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/scheduling/tasks.py#L24-L31. To
    run it manually, call the `update` function with a `user_id`.
-   **Interactive test:** Run the `simple_interactive_test` to create a
    test session, generate audio and ask follow‑up
    questionshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/content/simple_interactive_test.py#L30-L124.

## Configuration

Configuration is centralized in `modules/config.py`. It defines fallback
API keys and a country‑code mapping tablehttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/config.py#L10-L43. The
helper functions `get_openai_key`, `get_serpapi_key`,
`get_elevenlabs_key` and others read environment variables or use these
fallbackshttps://github.com/AdamZinebii/PrysmBackend/blob/main/modules/config.py#L46-L73. For security, always override the
fallback values using environment variables or a secrets manager.

## Contributing

Contributions are welcome! To propose a change or fix, fork the
repository, create a new branch, commit your changes with clear messages
and open a pull request. Please ensure that your code is well‑documented
and that you have added tests for new functionality.

## License

This repository does not currently specify a license. If you intend to
use this project in production or contribute to it, consider discussing
licensing with the project maintainers.
