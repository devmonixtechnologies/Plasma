<!doctype html>
<html lang="en">

<head>
  <?php include("inc/metas.php"); ?>
  <title>Case Study - CAI-powered API vulnerability discovery at Mercado Libre</title>
  <link rel="stylesheet" href="css/use-case.css">
  <link rel="stylesheet" href="css/about.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/Wruczek/Bootstrap-Cookie-Alert@gh-pages/cookiealert.css">
  <link href="css/worksans.css" rel="stylesheet">
  <meta name="description" content="CAI (Cybersecurity AI) framework discovers and demonstrates API vulnerabilities at Mercado Libre through automated enumeration attacks. AI-powered security testing reveals user data exposure risks." />
  <meta name="keywords" content="MercadoLibre, AI, robots, cybersecurity" />
  
</head>

<body class="research certification">
  <?php include("inc/menu.php"); ?>
  
  <div class="use-case-b">
    <div class="container">
      <div class="row">
        <div class="">
          <img class="img-responsive d-none d-sm-block" src="img/header-mercado-libre.png" alt="Card image">
          <!-- <img class="img-responsive d-sm-none" src="img/header_ris_jr_mobile.jpg" alt="Card image"> -->
        </div>
      </div>
    </div>
  </div>
  
  <!-- PROMPT: Search throughout the document and find all comments wherein TEMPLATE-TODO is present. In those cases, replace the content below as appropriate by using the following content from the jsonl file using only the last two lines. -->
  <div class="container-fluid">
    <div class="row">
      <div class="container">
        <div class="row py-4 pb-2">
          <div class="col-12 col-lg-6 col-xl-6">
            <h4 class="linkotherservices"><a href="case-studies-robot-cybersecurity.php"><i class="fa fa-chevron-left"></i> Other case studies</a></h4>
            
            <h2 class="pb-4">The use case</h2>
            <!-- TEMPLATE-TODO: the following text describe what the exercise from the JSONL is all about, including a short description of the target. For that, search on the internet for information -->
            <p class="pb-2">
              Mercado Libre's public API exposed user profiles without any form of authentication or rate limiting. This misconfiguration made it possible to conduct large-scale user enumeration attacks. Using only sequential user IDs, attackers could extract personal information such as usernames, account types, geographic locations, and profile permalinks. Alias Robotics, through its CAI (Cybersecurity AI) framework, created an automated testing methodology to explore this vulnerability and assess its potential impact.
            </p>
            <p class="pb-4">
              The CAI-driven exercise included rapid API requests using concurrent threads to emulate an adversary collecting user data at scale. The exercise successfully retrieved detailed account metadata from hundreds of users, proving the viability of mass data harvesting. The resulting insights serve as a compelling demonstration of a bug bounty exercise.
            </p>
            
          </div>
          <div class="col-12 col-lg-6 col-xl-6">
            <img class="img-responsive d-none d-sm-block attack" src="img/white-hack-case.png">
            <img class="img-responsive d-sm-none attack-m" src="img/white-hack-case.png">
          </div>
          
          <div class="col-xl-1 col-lg-1"></div>
          <div class="col-12 col-xl-7 col-lg-6 col-texto"></div>
        </div>
      </div>
    </div>
  </div>
  
  
  <!-- multimedia section -->
  <div class="container-fluid supported2">
    <div class="row">
      <div class="container">
        <div class="row py-5">
          <div class="col-12 col-lg-9 col-xl-9 video">
            <video controls style="width: 100%; height: auto; max-width: 100%;">
              <source src="videos/mercadolibre.mp4" type="video/mp4">
              Your browser does not support the video tag.
            </video>
          </div>
          
          <!-- TEMPLATE-TODO: provide a title and a short description of what happens in the JSONL file -->
          <div class="col-12 col-lg-3 col-xl-3 bullet-video align-self-end">
            <h5 class="" style="color:#1c1c1c; font-weight:700">
              Demonstration of Mass Enumeration Against Mercado Libre's Public API
            </h5>
            <p style="color:grey" class="pb-4">
              In this video, we leverage CAI (Cybersecurity AI) to automate the enumeration of Mercado Libre user accounts. The footage captures the real-time gathering of user data by issuing thousands of requests against the unauthenticated API. The lack of rate limiting or CAPTCHA enforcement is highlighted, showcasing how attackers could exploit this behavior to scrape user profiles for malicious purposes or competitive intelligence.
            </p>
            
            <a href="https://youtu.be/5JJ_X6dRv70" class="btn-flecha btn-readmore">
              <span class="circle"><span class="icon arrow"></span></span><span class="button-text">Video</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>  
  
  
  
  <div class="container-fluid">
    <div class="row py-4">
      <div class="col-12 col-lg-12 col-xl-12">
        <div class="row">
          <div class="container">
            <div class="row">
              <div class="col-12 col-sm-12 col-lg-12 col-xl-12 pt-5">
                
                <h2 class="py-4"><a style="color:#63bfab">Cybersecurity AI (CAI)</a>, the <i>de facto</i> scaffolding for building AI security</h2>
                <p class="pb-2">
                  CAI represents the first open-source framework specifically designed to democratize advanced security testing through specialized AI agents. By 2028, most cybersecurity actions will be autonomous, with humans teleoperating, making CAI's approach to AI-powered vulnerability discovery increasingly critical for organizational security.
                  The framework transcends theoretical benchmarks by enabling practical security outcomes. CAI achieved first place among AI teams and secured a top-20 position worldwide in the "AI vs Human" CTF live Challenge, earning a monetary reward and various other prizes and bounties ever since then. This performance demonstrates that AI-powered security testing can compete with and often exceed human capabilities in vulnerability discovery.
                </p>
                <a href="https://github.com/aliasrobotics/CAI" class="btn btn-relleno find-more">Explore CAI's source code <span>&#10095;</span></a>                                                  
              </div>              
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>  
  
  <!-- actors section -->
  <div class="container-fluid py-4 supported-rpk">
    <div class="row">
      <div class="container">
        <div class="row justify-content-center">
          <div class="col-12">
            <h2 class="py-4 " style="color:#333333; font-weight: bold;">Actors</h2>
            <div class="separator"></div>
          </div>
          
          <!-- User -->
          <div class="col-6 col-lg-2 col-xl-2">
            <img class="icono-us-4" src="img/icono-us-1-black.svg">
            <p style="color:#333333">
              User: </br>
              <a style="color:#63bfab">Researcher, hacker or you (yourself)</a>
            </p>
          </div>
          
          <!-- Tool (CAI) -->
          <div class="col-6 col-lg-2 col-xl-2">
            <img class="icono-us-4" src="img/icono-us-3-black.svg">
            <p style="color:#333333">
              Tool:<br> 
              <a style="color:#63bfab">CAI</a> 
              <!-- <br>(<a style="color:#63bfab">C</a>ybersecurity <a style="color:#63bfab">AI</a>) -->
            </p>
          </div>
          
          <!-- LLM Model -->
          <div class="col-6 col-lg-2 col-xl-2">
            <img class="icono-us-4" src="img/si-black.svg">
            <p style="color:#333333">
              LLM Model </br>
              <!-- TEMPLATE-TODO: the following text should be adapted to the model used throughout the JSONL file -->
              <a style="color:#63bfab; font-family: SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;">alias0</a>
            </p>
          </div>
          
          
          <!-- Target -->
          <div class="col-6 col-lg-2 col-xl-2">
            <img class="icono-us-4" src="img/manufacturer-black.svg">
            <p style="color:#333333">
              Target:</br>
              <!-- TEMPLATE-TODO: the following text should be adapted to the target of the JSONL file -->
              <a style="color:#63bfab">Mercado Libre</a>
            </p>
          </div>
          
        </div>
      </div>
    </div>
  </div>
  
  
  <div class="container-fluid">
    <div class="row">
      <div class="container">
        <div class="row py-5 pb-5 top">
          <div class="col-12 col-lg-12 col-xl-12">
            <!-- TEMPLATE-TODO: the following text should be adapted to the target of the JSONL file -->
            <h2 class="py-2"> About Mercado Libre</h2>
            <p>
              Mercado Libre is Latin America's largest e-commerce and fintech ecosystem, operating in over 18 countries including Argentina, Brazil, Mexico, and Chile. Founded in 1999, the platform facilitates millions of daily transactions by providing a wide range of services including online retail, digital payments (via Mercado Pago), logistics solutions, and advertising. With over 100 million active users, Mercado Libre handles sensitive user data and financial transactions at massive scale.
            </p>
            <p>
              Given its expansive user base and integration with banking infrastructure, Mercado Libre represents a high-value target for cybersecurity threats. As the platform continues to scale and innovate, ensuring robust API security and data privacy has become critical. This case study explores a vulnerability in their user-facing API that could expose personal information at scale if left unmitigated.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  
  <div class="about-map">
    <img src="img/top-map.jpg" alt="">
    <div class="value-about">
      <div class="container">
        <div class="row">
          <div class="col-xl-4 col-lg-12">
            <div class="col-12 col-md-5 col-lg-5 col-xl-12 col-number1">
              <h2>Time for the exercise</h2>
              <h3>minutes</h3>
              <div class="frame-style"></div>
              <!-- TEMPLATE-TODO: the following text should be adapted to the time for the exercise of the JSONL file -->
              <p class="angle-up"><strong><span class="counter">10</span></strong></p>
              <br><br>
            </div>
            <div class="col-12 col-md-5 col-lg-5 col-xl-12 col-number2">
              <h2>Cost</h2>
              <h3>in EUR</h3>
              <div class="frame-style"></div>
              <!-- TEMPLATE-TODO: the following text should be adapted to the cost of the exercise of the JSONL file -->
              <p><strong><span class="counter">2.38 €</span></strong></p>
            </div>
          </div>
          <div class="col-xl-8 col-lg-12">
            <div class="case-study-summary px-4 py-5">                
              <div class="row">
                <div class="col-12 col-lg-6 mb-4">
                  <div class="summary-card p-4" style="background: rgba(255,255,255,0.9); border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); height: 100%;">
                    <h4 style="color: #254450; font-weight: bold; margin-bottom: 15px;">🎯 THE CHALLENGE</h4>
                    <!-- TEMPLATE-TODO: the following text should be adapted to the challenge of the JSONL file -->
                    <p style="color: #333; font-size: 1.1rem; line-height: 1.6;">
                      Mercado Libre's publicly exposed user API permitted unrestricted access to user profile data without requiring authentication tokens or anti-bot controls. This misconfiguration enabled attackers to enumerate user accounts using sequential IDs. During the test, Alias Robotics simulated a real-world adversary, collecting over 100 user records in under a minute. The absence of rate limiting, along with exposed metadata, highlighted the potential for large-scale user data harvesting and increased phishing campaign risk.
                    </p>
                    
                  </div>
                </div>
                
                <div class="col-12 col-lg-6 mb-4">
                  <div class="summary-card p-4" style="background: rgba(255,255,255,0.9); border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); height: 100%;">
                    <h4 style="color: #254450; font-weight: bold; margin-bottom: 15px;">🛡️ THE SOLUTION</h4>
                    <!-- TEMPLATE-TODO: the following text should be adapted to the solution of the JSONL file -->
                    <p style="color: #333; font-size: 1.1rem; line-height: 1.6;">
                      To validate and demonstrate the risk, the CAI framework was deployed to script and run enumeration attacks in a controlled environment. By using multi-threaded concurrent requests and dynamic progress tracking, CAI provided concrete evidence of the vulnerability's scale and impact. Key metrics such as enumeration success rate, location-based user distributions, and response latencies were recorded. These results provided actionable intelligence for reporting the issue to Mercado Libre's security response team.
                    </p>
                    
                  </div>
                </div>
              </div>
              
              <div class="row">
                <div class="col-12 col-lg-6 mb-4">
                  <div class="summary-card p-4" style="background: rgba(255,255,255,0.9); border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); height: 100%;">
                    <h4 style="color: #254450; font-weight: bold; margin-bottom: 15px;">🔬 KEY ARTIFACTS</h4>
                    <!-- TEMPLATE-TODO: the following text should be adapted to the key artifacts of the JSONL file -->
                    <ul style="color: #333; font-size: 1.1rem; line-height: 1.6; margin: 0; padding-left: 20px;">
                      <li>Custom-built CAI automation script for user profile enumeration</li>
                      <li>Detailed analysis of user types and geographic dispersion</li>
                      <li>Rate-limiting probe tests showing absence of throttling or blocking</li>
                    </ul>
                    
                  </div>
                </div>
                
                <div class="col-12 col-lg-6 mb-4">
                  <div class="summary-card p-4" style="background: rgba(255,255,255,0.9); border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); height: 100%;">
                    <h4 style="color: #254450; font-weight: bold; margin-bottom: 15px;">✅ RESULTS ACHIEVED</h4>
                    <!-- TEMPLATE-TODO: the following text should be adapted to the results achieved of the JSONL file -->
                    <ul style="color: #333; font-size: 1.1rem; line-height: 1.6; margin: 0; padding-left: 20px;">
                      <li>Exposed vulnerability in Mercado Libre's user API</li>
                      <li>Documented enumeration of >100 user profiles in less than 60 seconds</li>
                      <li>Gathered compelling evidence for bug bounty submission and coordinated disclosure</li>
                    </ul>
                    
                  </div>
                </div>
              </div>
              
              <div class="row mt-4">
                <div class="col-12 text-center">
                  <div class="key-benefits p-4" style="background: linear-gradient(135deg, #63bfab, #529d86); border-radius: 15px; color: white;">
                    <h4 style="color: white; font-weight: bold; margin-bottom: 20px;">KEY BENEFITS</h4>
                    <div class="row">
                      <div class="col-12 col-md-4 mb-2">
                        <span style="font-size: 1.2rem; font-weight: 600;">🔒 AI-powered Security</span>
                      </div>
                      <div class="col-12 col-md-4 mb-2">
                        <span style="font-size: 1.2rem; font-weight: 600;">⚡ Cost-effective and fast</span>
                      </div>
                      <div class="col-12 col-md-4 mb-2">
                        <span style="font-size: 1.2rem; font-weight: 600;">🤖 Robot Protection</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <img src="img/bottom-map.jpg" alt="">
  </div>
  
  
  
  
  <div class="container-fluid top" style="text-align:center">
    <div class="row">
      <div class="container">
        <div class="row">
          <div class="col-12 col-lg-12 col-xl-12 pb-5" style="margin-bottom:3em;">
            <a href="https://github.com/aliasrobotics/CAI" class="btn btn-relleno find-more">Use CAI <span>&#10095;</span></a>
            <!-- TEMPLATE: the following button should be shown only if alias0 is the model used -->
            <a href="https://github.com/aliasrobotics/CAI" class="btn btn-linea find-more">Learn about <b style="color:#63bfab; font-family: SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;">alias0</b> <span>&#10095;</span></a>
          </div>
        </div>
      </div>
    </div>
  </div>
  <?php include("inc/footer.php"); ?>
</body>

</html>