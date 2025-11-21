import { useState, useRef, useEffect } from "react"; 
import { useNavigate } from "react-router-dom"; // ✨ 1. IMPORT ADDED
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Switch } from "@/components/ui/switch";
import { Send, MessageSquare, Camera, Settings, LogOut, X, Mic, MicOff, Volume2, VolumeX } from "lucide-react"; 
import videoSrc from "@/assets/final_video.mp4";
import avatarImage from "@/assets/feroze-avatar-new.jpg";

const Dashboard = () => {
  const navigate = useNavigate(); // ✨ 2. HOOK ADDED

  const [message, setMessage] = useState("");
  const [isAvatarMode, setIsAvatarMode] = useState(true);
  const [isTalking, setIsTalking] = useState(false);
  
  // Voice Toggle State
  const [isVoiceOn, setIsVoiceOn] = useState(true);

  // Voice State
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);
  
  // Auto-Send Trigger State
  const [voiceTrigger, setVoiceTrigger] = useState<string | null>(null);

  // User Profile State
  const [userProfile, setUserProfile] = useState({
    name: "John Doe",
    email: "john@example.com"
  });

  const [messages, setMessages] = useState<Array<{ id: number; text: string; sender: "user" | "ai" }>>([]);
  const [recentChats] = useState([
    { id: 1, title: "Portfolio Analysis", date: "Today" },
    { id: 2, title: "Investment Strategy", date: "Yesterday" },
    { id: 3, title: "Market Trends", date: "2 days ago" },
    { id: 4, title: "Risk Assessment", date: "1 week ago" },
  ]);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null); 

  // 🔥 3. SECURITY GUARD: Redirect if no token
  useEffect(() => {
    const token = localStorage.getItem("authToken");
    if (!token) {
      navigate("/auth");
    }
  }, []);

  // LOAD USER PROFILE
  useEffect(() => {
    const storedEmail = localStorage.getItem("userEmail");
    const storedName = localStorage.getItem("userName");

    if (storedEmail) {
      setUserProfile({
        name: storedName || "Valued Client",
        email: storedEmail
      });
    }
  }, []);

  // Auto Send Effect
  useEffect(() => {
    if (voiceTrigger) {
      handleSend(voiceTrigger); 
      setVoiceTrigger(null);    
    }
  }, [voiceTrigger]);

  // 🔥 FIXED MUTE EFFECT: Removed buggy condition
  useEffect(() => {
    if (audioRef.current) {
      if (!isVoiceOn) {
        audioRef.current.pause();
        setIsTalking(false);
      } else {
        // Agar audio exist karta hai aur khatam nahi hua, toh bajao
        if (audioRef.current.paused && !audioRef.current.ended && audioRef.current.src) {
          audioRef.current.play().catch(e => console.log("Playback error", e));
          setIsTalking(true);
        }
      }
    }
  }, [isVoiceOn]);

  // --- 🎤 SPEECH RECOGNITION SETUP ---
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US'; 

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setIsRecording(false);
        setVoiceTrigger(transcript); 
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech error:', event.error);
        setIsRecording(false);
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    }
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition not supported in this browser.");
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };
  
  const handleScan = async () => {
    if (isScanning) {
      if (videoRef.current && videoRef.current.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
        tracks.forEach((track) => track.stop());
        videoRef.current.srcObject = null;
      }
      setIsScanning(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: false,
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setIsScanning(true);

        stream.getVideoTracks()[0].onended = () => {
          setIsScanning(false);
        };

      } catch (err) {
        console.error("Error starting screen share:", err);
        setIsScanning(false);
      }
    }
  };

  const captureScreenshot = (): string | null => {
    if (!videoRef.current || !isScanning) return null;
    try {
      const video = videoRef.current;
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL("image/jpeg", 0.7);
    } catch (err) {
      console.error("Error capturing screenshot:", err);
      return null;
    }
  };

  const handleSend = async (manualText?: string) => {
    const textToSend = typeof manualText === 'string' ? manualText : message;

    if (!textToSend.trim()) return;

    const token = localStorage.getItem("authToken");
    if (!token) {
      alert("You are not logged in. Please login first.");
      return;
    }

    const newMessage = {
      id: Date.now(),
      text: textToSend,
      sender: "user" as const,
    };
    setMessages((prev) => [...prev, newMessage]);
    
    setMessage(""); 

    let screenshot: string | null = null;
    let endpoint = "http://localhost:8000/api/chat";
    let body: any = { question: textToSend };

    if (isScanning) {
      screenshot = captureScreenshot();
      if (screenshot) {
        endpoint = "http://localhost:8000/api/consult"; 
        body = { question: textToSend, screenshot: screenshot }; 
        handleScan(); 
      }
    }

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify(body),
      });

      if (response.status === 401 || response.status === 403) {
        alert("Session expired. Please login again.");
        return;
      }

      const data = await response.json();

      const aiResponse = {
        id: Date.now() + 1,
        text: data.answer || "I couldn't process that.",
        sender: "ai" as const,
      };
      setMessages((prev) => [...prev, aiResponse]);

      if (data.audio_url) {
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
        }
        const audioUrl = `http://localhost:8000${data.audio_url}`;
        audioRef.current = new Audio(audioUrl);
        
        if (isVoiceOn) {
          audioRef.current.play()
            .then(() => setIsTalking(true))
            .catch(e => console.log("Playback error", e));
        }

        audioRef.current.onended = () => setIsTalking(false);
      }
    } catch (error) {
      console.error("Error fetching response:", error);
      setMessages((prev) => [...prev, { id: Date.now(), text: "Server connection failed.", sender: "ai" }]);
      setIsTalking(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-white"> 
      <aside className="w-80 border-r border-border bg-card flex flex-col">
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <Avatar className="w-12 h-12">
              <AvatarImage src={avatarImage} />
              <AvatarFallback className="bg-primary text-primary-foreground">
                {userProfile.name.charAt(0)}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <p className="font-semibold text-foreground">{userProfile.name}</p>
              <p className="text-sm text-muted-foreground truncate max-w-[180px]" title={userProfile.email}>
                {userProfile.email}
              </p>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-muted-foreground mb-3">Recent Chats</h3>
          </div>
          <ScrollArea className="h-[calc(100vh-280px)]">
            <div className="px-4 space-y-2">
              {recentChats.map((chat) => (
                <button key={chat.id} className="w-full text-left p-3 rounded-lg hover:bg-accent transition-colors group">
                  <div className="flex items-start gap-3">
                    <MessageSquare className="w-4 h-4 mt-1 text-primary" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-foreground truncate">{chat.title}</p>
                      <p className="text-xs text-muted-foreground">{chat.date}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>
        <div className="p-4 border-t border-border space-y-2">
          <Button variant="ghost" className="w-full justify-start" size="sm"><Settings className="w-4 h-4 mr-2" /> Settings</Button>
          
          {/* ✨ LOGOUT BUTTON clears data */}
          <Button 
            variant="ghost" 
            className="w-full justify-start text-destructive" 
            size="sm"
            onClick={() => {
              localStorage.clear();
              window.location.href = "/auth"; 
            }}
          >
            <LogOut className="w-4 h-4 mr-2" /> Logout
          </Button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col relative">
        <div className="absolute top-6 right-6 z-10 flex items-center gap-3 bg-card px-4 py-2 rounded-full shadow-lg border border-border">
          <span className={`text-sm font-medium ${isAvatarMode ? 'text-foreground' : 'text-muted-foreground'}`}>Avatar Mode</span>
          <Switch checked={!isAvatarMode} onCheckedChange={(checked) => setIsAvatarMode(!checked)} />
          <span className={`text-sm font-medium ${!isAvatarMode ? 'text-foreground' : 'text-muted-foreground'}`}>Chat Mode</span>
        </div>

        <div className="flex-1 overflow-hidden">
          {isAvatarMode ? (
            <div className="h-full flex items-center justify-center">
              <div className="relative">
                {isTalking ? (
                  <video src={videoSrc} loop muted playsInline autoPlay className="h-[70vh] w-auto object-contain" />
                ) : (
                  <img src={avatarImage} className="h-[70vh] w-auto object-contain" alt="Feroze Idle" />
                )}
              </div>
            </div>
          ) : (
            <ScrollArea className="h-full">
              <div className="max-w-4xl mx-auto p-6 space-y-4">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-[60vh]">
                    <p className="text-muted-foreground text-lg">Start a conversation with Feroze</p>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[70%] rounded-2xl px-4 py-3 ${msg.sender === "user" ? "bg-primary text-primary-foreground" : "bg-card text-card-foreground border border-border"}`}>
                        <p className="text-sm">{msg.text}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          )}
        </div>

        <div className="p-6">
          <div className="max-w-4xl mx-auto">
            <div className="relative flex items-center gap-2 p-2 rounded-2xl bg-card shadow-lg border border-border">
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSend()}
                placeholder={isScanning ? "Ask about the shared screen..." : "Ask Feroze regarding your portfolio..."}
                className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
              />
              
              <div className="flex items-center gap-1">
                
                <Button
                  size="icon"
                  variant="ghost"
                  className="rounded-xl hover:bg-accent"
                  onClick={() => setIsVoiceOn(!isVoiceOn)}
                  title={isVoiceOn ? "Mute AI Voice" : "Unmute AI Voice"}
                >
                  {isVoiceOn ? <Volume2 className="w-5 h-5 text-gray-700" /> : <VolumeX className="w-5 h-5 text-red-500" />}
                </Button>

                <Button
                  size="icon"
                  variant="ghost"
                  className={`rounded-xl hover:bg-accent ${isRecording ? 'bg-red-100 text-red-600 animate-pulse' : ''}`}
                  onClick={toggleRecording}
                  title="Speak"
                >
                  {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                </Button>

                <Button
                  size="icon"
                  variant="ghost"
                  className={`rounded-xl hover:bg-accent ${isScanning ? 'bg-red-100 text-red-600 hover:bg-red-200' : ''}`}
                  onClick={handleScan}
                  title="Start/Stop Screen Share"
                >
                  <Camera className="w-5 h-5" />
                </Button>
                
                <Button
                  size="icon"
                  className="rounded-xl bg-primary hover:bg-primary/90"
                  onClick={() => handleSend()} 
                  disabled={!message.trim()}
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
        
        <video ref={videoRef} autoPlay style={{ display: "none" }} />
      </main>
    </div>
  );
};

export default Dashboard;