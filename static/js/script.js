function toggleLoginPassword() {

    const passwordField =
        document.getElementById("loginPassword");

    const eyeIcon =
        document.getElementById("eyeIcon");

    if (passwordField.type === "password") {

        passwordField.type = "text";

        eyeIcon.classList.remove("bi-eye");
        eyeIcon.classList.add("bi-eye-slash");

    } else {

        passwordField.type = "password";

        eyeIcon.classList.remove("bi-eye-slash");
        eyeIcon.classList.add("bi-eye");
    }
}