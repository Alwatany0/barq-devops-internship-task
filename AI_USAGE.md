# AI usage disclosure

I used AI while working on this task. At the time, I was also studying DevOps because I have been interested in the field for a long time but had not previously had a real opportunity to work in it.

I used ChatGPT (GPT-5.6 Luna) mainly as a learning and troubleshooting assistant while doing the task. I was learning the concepts and commands while applying them to the actual environment, so the task was also a way for me to understand how DevOps works in practice.

* **Tool/model:** ChatGPT (GPT-5.6 Luna)
* **Purpose:** Learn DevOps concepts, understand Docker/Compose and NGINX behavior, troubleshoot errors, understand CI, and get help structuring the required documentation.
* **Files or decisions affected:** Dockerfile, `docker-compose.yml`, `nginx/nginx.conf`, `validate.py`, `failure_test.py`, `backup.sh`, `restore.sh`, CI workflow, and the documentation files.
* **What I changed or rejected:** I used AI suggestions as guidance, but I changed commands and configurations when they did not match the actual environment or the task requirements. I also rejected suggestions when they were not appropriate for the setup.
* **How I independently verified it:** I ran the commands myself and checked the actual Docker Compose state, container health, networks, ports, HTTP endpoints, load balancing, failure recovery, database persistence, backup/restore, and GitHub Actions CI. I only kept results that I could reproduce and verify in the environment.
* **Related commits:** The work is split across the progressive commits in the repository, including `7babf30`, `548e8dc`, `a5e7eff`, `352eb86`, `25bdd3d`, `fed0147`, `d395439`, and `efc76d1`.

AI was therefore part of my learning process as well as my troubleshooting workflow. I still had to understand the changes, apply them to the environment, verify the results, and document what actually happened.
