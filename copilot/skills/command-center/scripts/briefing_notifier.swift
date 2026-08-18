import AppKit
import Darwin
import Foundation
import UserNotifications

final class NotificationDelegate: NSObject, NSApplicationDelegate, UNUserNotificationCenterDelegate {
    var window: NSWindow?
    var briefingPath: String?

    func showLatestBriefing() {
        let directory = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Command Center/Briefings")
        guard let path = try? FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        )
        .filter({ $0.pathExtension == "md" })
        .sorted(by: { first, second in
            let firstDate = (try? first.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            let secondDate = (try? second.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            return firstDate > secondDate
        })
        .first else {
            return
        }
        showBriefing(path: path.path)
    }

    @objc func openInObsidian() {
        guard let briefingPath else { return }
        let fileURL = URL(fileURLWithPath: briefingPath)
        if let appURL = NSWorkspace.shared.urlForApplication(
            withBundleIdentifier: "md.obsidian"
        ) {
            NSWorkspace.shared.open(
                [fileURL],
                withApplicationAt: appURL,
                configuration: NSWorkspace.OpenConfiguration()
            )
        } else {
            NSWorkspace.shared.open(fileURL)
        }
    }

    func styledBriefing(_ content: String) -> NSAttributedString {
        let result = NSMutableAttributedString()
        let bodyFont = NSFont.systemFont(ofSize: 14)
        let headingFont = NSFont.systemFont(ofSize: 17, weight: .semibold)
        let titleFont = NSFont.systemFont(ofSize: 25, weight: .bold)
        let paragraphStyle = NSMutableParagraphStyle()
        paragraphStyle.paragraphSpacing = 8
        paragraphStyle.lineSpacing = 3

        for line in content.split(separator: "\n", omittingEmptySubsequences: false) {
            let text = String(line)
            let leadingSpaces = text.prefix(while: { $0 == " " }).count
            let trimmedText = text.trimmingCharacters(in: .whitespaces)
            let isTitle = text.hasPrefix("# ")
            let isHeading = text.hasPrefix("## ")
            let displayText: String
            let font: NSFont
            let color: NSColor
            if isTitle {
                displayText = String(text.dropFirst(2))
                font = titleFont
                color = .labelColor
            } else if isHeading {
                displayText = String(text.dropFirst(3))
                font = headingFont
                color = displayText.localizedCaseInsensitiveContains("επείγον")
                    ? .systemRed
                    : .controlAccentColor
            } else if trimmedText.hasPrefix("- ") {
                displayText = "• " + trimmedText.dropFirst(2)
                font = bodyFont
                color = .labelColor
            } else {
                displayText = text
                font = bodyFont
                color = .secondaryLabelColor
            }
            let lineStyle = paragraphStyle.mutableCopy() as! NSMutableParagraphStyle
            lineStyle.headIndent = CGFloat(leadingSpaces / 2) * 22
            lineStyle.firstLineHeadIndent = lineStyle.headIndent
            result.append(
                NSAttributedString(
                    string: displayText + "\n",
                    attributes: [
                        .font: font,
                        .foregroundColor: color,
                        .paragraphStyle: lineStyle,
                    ]
                )
            )
        }
        return result
    }

    func showBriefing(path: String) {
        guard let content = try? String(contentsOfFile: path, encoding: .utf8) else {
            return
        }
        briefingPath = path
        let textView = NSTextView(frame: .zero)
        textView.textStorage?.setAttributedString(styledBriefing(content))
        textView.isEditable = false
        textView.textContainerInset = NSSize(width: 20, height: 20)

        let scrollView = NSScrollView(frame: .zero)
        scrollView.hasVerticalScroller = true
        scrollView.documentView = textView
        scrollView.autohidesScrollers = true

        let openButton = NSButton(
            title: "Άνοιγμα στο Obsidian",
            target: self,
            action: #selector(openInObsidian)
        )
        openButton.bezelStyle = .rounded
        let buttonBar = NSStackView(views: [openButton])
        buttonBar.orientation = .horizontal
        buttonBar.alignment = .centerY
        buttonBar.edgeInsets = NSEdgeInsets(top: 0, left: 20, bottom: 16, right: 20)

        let contentView = NSStackView(views: [scrollView, buttonBar])
        contentView.orientation = .vertical
        contentView.alignment = .leading
        contentView.distribution = .fill
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.widthAnchor.constraint(greaterThanOrEqualToConstant: 700).isActive = true
        scrollView.heightAnchor.constraint(greaterThanOrEqualToConstant: 600).isActive = true

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 820, height: 760),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Command Center — Briefing"
        window.contentView = contentView
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        self.window = window
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .sound])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let userInfo = response.notification.request.content.userInfo
        if let url = userInfo["url"] as? String,
           !url.isEmpty,
           let target = URL(string: url) {
            NSWorkspace.shared.open(target)
        } else if let path = userInfo["path"] as? String {
            showBriefing(path: path)
        }
        completionHandler()
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
ProcessInfo.processInfo.disableAutomaticTermination("Command Center briefing window")
let delegate = NotificationDelegate()
app.delegate = delegate
let center = UNUserNotificationCenter.current()
center.delegate = delegate

func sendNotification(
    title: String,
    subtitle: String,
    body: String,
    userInfo: [AnyHashable: Any]
) {
    center.requestAuthorization(options: [.alert, .sound]) { granted, error in
        if let error {
            fputs("Notification authorization failed: \(error)\n", stderr)
            exit(2)
        }
        guard granted else {
            fputs("Notification authorization was denied.\n", stderr)
            exit(2)
        }
        let content = UNMutableNotificationContent()
        content.title = title
        content.subtitle = subtitle
        content.body = body
        content.sound = .default
        content.userInfo = userInfo
        let request = UNNotificationRequest(
            identifier: "command-center-\(UUID().uuidString)",
            content: content,
            trigger: nil
        )
        center.add(request) { error in
            if let error {
                fputs("Notification delivery failed: \(error)\n", stderr)
                exit(2)
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                app.terminate(nil)
            }
        }
    }
}

if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "--show" {
    delegate.showBriefing(path: CommandLine.arguments[2])
    app.run()
    exit(0)
}

if CommandLine.arguments.count >= 5, CommandLine.arguments[1] == "--call" {
    let eventTitle = CommandLine.arguments[2]
    let startTime = CommandLine.arguments[3]
    let meetingURL = CommandLine.arguments[4]
    let body = meetingURL.isEmpty
        ? "Ξεκινά στις \(startTime)"
        : "Ξεκινά στις \(startTime) · \(meetingURL)"
    sendNotification(
        title: "Call σε 15 λεπτά",
        subtitle: eventTitle,
        body: body,
        userInfo: meetingURL.isEmpty ? [:] : ["url": meetingURL]
    )
    app.run()
    exit(0)
}

if CommandLine.arguments.count == 1 {
    delegate.showLatestBriefing()
    app.run()
    exit(0)
}

guard CommandLine.arguments.count >= 4 else {
    fputs("Usage: briefing-notifier KIND PATH PREVIEW\n", stderr)
    exit(2)
}

let kind = CommandLine.arguments[1]
let path = CommandLine.arguments[2]
let preview = CommandLine.arguments[3]
sendNotification(
    title: "Command Center",
    subtitle: "\(kind) briefing",
    body: preview,
    userInfo: ["path": path]
)
app.run()
