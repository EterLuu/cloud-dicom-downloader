import re
import os
import asyncio
import aiohttp

# ⚠️ 替换为你访问医院系统真实的公网地址和端口！
# 例如："https://yyx.zy91.com:5443" 或 "https://yyx.zy91.com:8443"
REAL_HOST = "https://yyx.zy91.com:5443"  

async def download_image(session, url, save_path, retries=3):
    # 将本地测试地址替换为公网真实地址
    if "localhost:1000" in url:
        url = url.replace("http://localhost:1000", REAL_HOST)
        
    for i in range(retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "*/*"
            }
            # 禁用 SSL 验证，增加超时时间
            async with session.get(url, headers=headers, ssl=False, timeout=20) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(save_path, 'wb') as f:
                        f.write(content)
                    print(f"  ✅ 下载成功: {os.path.basename(save_path)}")
                    return True
                else:
                    print(f"  ⚠️ 状态异常 {response.status}: {os.path.basename(save_path)}，准备重试...")
        except Exception as e:
            if i == retries - 1:
                print(f"  ❌ 下载失败 {os.path.basename(save_path)}: {e}")
        
        await asyncio.sleep(1)
        
    return False

async def main():
    html_file = "viewer.html" 
    
    if not os.path.exists(html_file):
        print(f"❌ 找不到文件 {html_file}。请确保把 HTML 源码保存在这个文件中。")
        return
        
    print("[*] 正在逐行扫描 HTML，精准提取图像链接...")
    with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    tasks = []
    # 限制最大并发数为 15，防止把医院服务器冲挂或被封 IP
    semaphore = asyncio.Semaphore(15)

    async def bounded_download(session, url, save_path):
        async with semaphore:
            await download_image(session, url, save_path)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        count = 0
        for line in lines:
            # 只要这一行包含 'var imgInfo' 和 'imageURL'，就是目标行
            if 'var imgInfo' in line and '"imageURL"' in line:
                url_match = re.search(r'"imageURL"\s*:\s*"([^"]+)"', line)
                num_match = re.search(r'"imageNumber"\s*:\s*"(\d+)"', line)
                ser_match = re.search(r'serObj(\d+)\.serIndex', line)
                
                if not url_match:
                    continue
                    
                url = url_match.group(1)
                img_num = int(num_match.group(1)) if num_match else count
                ser_index = int(ser_match.group(1)) if ser_match else 0
                
                # 创建序列文件夹
                save_dir = f"./DICOM_Download/Series_{ser_index}"
                os.makedirs(save_dir, exist_ok=True)
                
                # 文件名：IMG_0001.dcm
                save_path = os.path.join(save_dir, f"IMG_{img_num:04d}.dcm")
                count += 1
                
                # 跳过已经下载完的非空文件
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    continue
                    
                tasks.append(bounded_download(session, url, save_path))
                
        if tasks:
            print(f"\n🚀 提取成功！即将开始下载 {len(tasks)} 张图像，请耐心等待...")
            await asyncio.gather(*tasks)
            print("\n🎉 全部下载任务执行完毕！请检查 DICOM_Download 文件夹。")
        else:
            print(f"\n✅ 扫描到 {count} 张图片，本地已存在所有图像文件，无需重复下载。")

if __name__ == "__main__":
    asyncio.run(main())