fn main() {
    let mut std_cmd = std::process::Command::new("docker");
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        std_cmd.creation_flags(0x08000000);
    }
    let _cmd = tokio::process::Command::from(std_cmd);
}
