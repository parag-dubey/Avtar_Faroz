import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import avatarImage from "@/assets/feroze-avatar-new.jpg"; 

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  // 🔥 CHANGE: Ab hum Python Backend se baat karenge
  const BASE_URL = "http://localhost:8000";

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      let response;
      
      if (isLogin) {
        // --- LOGIN ---
        response = await fetch(`${BASE_URL}/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ Email: email, Password: password })
        });
      } else {
        // --- REGISTER ---
        response = await fetch(`${BASE_URL}/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ Name: name, Email: email, Password: password })
        });
      }

      const data = await response.json();

      if (response.ok) {
        // Success Case
        toast({
          title: "Success",
          description: data.message,
        });

        if (isLogin) {
          // 🔒 SAVE ASLI JWT TOKEN
          localStorage.setItem("authToken", data.token); 
          
          // User Info Save karna
          if (data.user) {
            localStorage.setItem("userName", data.user.Name || "User");
            localStorage.setItem("userEmail", data.user.Email);
          }

          navigate("/dashboard");
        } else {
          // Register ho gaya, ab login karo
          setIsLogin(true);
          setPassword(""); // Clear password for safety
        }

      } else {
        // Error Case (Backend se aaya error dikhao)
        throw new Error(data.detail || "Authentication failed");
      }

    } catch (error: any) {
      console.error(error);
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-[hsl(210,100%,65%)] via-[hsl(200,100%,75%)] to-[hsl(195,100%,85%)]">
        <div className="absolute top-0 left-0 w-96 h-96 bg-white/30 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-[hsl(200,100%,90%)]/30 rounded-full blur-3xl animate-pulse-slow"></div>
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        <div className="bg-white/90 backdrop-blur-md rounded-3xl shadow-elegant p-8 border-4 border-white/50">
          
          <div className="mb-6 text-center">
            <img
              src={avatarImage}
              alt="Feroze Azeez"
              className="mx-auto h-24 w-24 rounded-full border-4 border-white/50 object-cover"
            />
            <h2 className="mt-4 text-3xl font-bold text-[hsl(200,95%,30%)]">
              {isLogin ? "Welcome Back" : "Create Account"}
            </h2>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            
            {!isLogin && (
              <div>
                <Label htmlFor="name" className="text-[hsl(220,15%,15%)]">Name</Label>
                <Input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="bg-white/90 text-[hsl(220,15%,15%)]"
                  placeholder="Your Name"
                />
              </div>
            )}

            <div>
              <Label htmlFor="email" className="text-[hsl(220,15%,15%)]">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-white/90 text-[hsl(220,15%,15%)]"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-[hsl(220,15%,15%)]">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-white/90 text-[hsl(220,15%,15%)]"
                placeholder="••••••••"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full text-lg py-6 h-auto rounded-full font-bold text-white border-4 border-white/30 transition-all duration-300 hover:scale-105"
              style={{
                background: 'linear-gradient(135deg, hsl(200 95% 45%) 0%, hsl(195 85% 55%) 100%)',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.2), inset 0 2px 4px rgba(255, 255, 255, 0.3)',
              }}
            >
              {loading ? "Processing..." : isLogin ? "Login" : "Sign Up"}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-[hsl(200,95%,35%)] hover:underline font-medium"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Login"}
            </button>
          </div>

          <div className="mt-4 text-center">
            <button
              onClick={() => navigate("/")}
              className="text-[hsl(220,15%,45%)] hover:underline text-sm"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Auth;