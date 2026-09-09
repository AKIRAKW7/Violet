/* =========================================================
   VIOLET — WEB INTERACTIONS
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* -----------------------------------------
       CONFIGURACIÓN
    ----------------------------------------- */

    /*
     * IMPORTANTE:
     * Reemplaza 1545625028714958990 por el Application ID
     * de tu bot en Discord.
     */
    const INVITE_URL =
        "https://discord.com/oauth2/authorize?client_id=1545625028714958990&permissions=8&scope=bot%20applications.commands";


    /* -----------------------------------------
       BOTONES DE INVITACIÓN
    ----------------------------------------- */

    document.querySelectorAll("[data-invite]").forEach(button => {

        button.addEventListener("click", event => {

            event.preventDefault();

            if (!INVITE_URL || !INVITE_URL.includes("1545625028714958990")) {
                alert("No se pudo configurar el enlace de invitación de Violet.");
                return;
            }

            window.open(
                INVITE_URL,
                "_blank",
                "noopener,noreferrer"
            );
        });

    });


    /* -----------------------------------------
       SCROLL SUAVE
    ----------------------------------------- */

    document.querySelectorAll('a[href^="#"]').forEach(link => {

        link.addEventListener("click", event => {

            const targetId = link.getAttribute("href");

            if (!targetId || targetId === "#") {
                return;
            }

            const target = document.querySelector(targetId);

            if (!target) {
                return;
            }

            event.preventDefault();

            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        });

    });


    /* -----------------------------------------
       ANIMACIONES AL APARECER
    ----------------------------------------- */

    const animatedElements = document.querySelectorAll(
        ".feature-card, .command-row, .market-section, " +
        ".discord-window, .invite-box, .faq-list"
    );

    const observer = new IntersectionObserver(
        entries => {

            entries.forEach(entry => {

                if (!entry.isIntersecting) {
                    return;
                }

                entry.target.classList.add("visible");

                observer.unobserve(entry.target);

            });

        },
        {
            threshold: 0.12
        }
    );

    animatedElements.forEach(element => {
        element.classList.add("reveal");
        observer.observe(element);
    });


    /* -----------------------------------------
       EFECTO DE MOVIMIENTO EN TARJETA DE VIOLET
    ----------------------------------------- */

    const violetCard = document.querySelector(".violet-card");

    if (violetCard && window.matchMedia("(pointer:fine)").matches) {

        document.addEventListener("mousemove", event => {

            const x = (window.innerWidth / 2 - event.clientX) / 80;
            const y = (window.innerHeight / 2 - event.clientY) / 80;

            violetCard.style.transform =
                `perspective(900px) rotateY(${-x}deg) rotateX(${y}deg)`;

        });

        document.addEventListener("mouseleave", () => {
            violetCard.style.transform =
                "perspective(900px) rotateY(0deg) rotateX(0deg)";
        });

    }


    /* -----------------------------------------
       NAVBAR AL HACER SCROLL
    ----------------------------------------- */

    const navbar = document.querySelector(".navbar");

    if (navbar) {

        window.addEventListener(
            "scroll",
            () => {

                if (window.scrollY > 40) {
                    navbar.classList.add("scrolled");
                } else {
                    navbar.classList.remove("scrolled");
                }

            },
            { passive: true }
        );

    }


    /* -----------------------------------------
       FECHA DINÁMICA DEL FOOTER
    ----------------------------------------- */

    const footerYear = document.querySelector(".footer-year");

    if (footerYear) {
        footerYear.textContent = new Date().getFullYear();
    }


    /* -----------------------------------------
       MENSAJE DE CARGA
    ----------------------------------------- */

    document.body.classList.add("loaded");

});
