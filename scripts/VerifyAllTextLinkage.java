import java.io.*;
import java.lang.invoke.*;
import java.util.*;
import java.util.zip.*;

public class VerifyAllTextLinkage {
    static class CP {
        int[] tag;
        Object[] value;
        CP(DataInputStream in) throws IOException {
            int n = in.readUnsignedShort();
            tag = new int[n]; value = new Object[n];
            for (int i=1; i<n; i++) {
                tag[i] = in.readUnsignedByte();
                value[i] = switch (tag[i]) {
                    case 1 -> in.readUTF();
                    case 3 -> in.readInt();
                    case 4 -> in.readFloat();
                    case 5 -> in.readLong();
                    case 6 -> in.readDouble();
                    case 7,8,16,19,20 -> in.readUnsignedShort();
                    case 9,10,11,12,17,18 -> new int[]{in.readUnsignedShort(), in.readUnsignedShort()};
                    case 15 -> new int[]{in.readUnsignedByte(), in.readUnsignedShort()};
                    default -> throw new IOException("Bad pool tag "+tag[i]);
                };
                if (tag[i]==5 || tag[i]==6) i++;
            }
        }
        String utf(int i) { return (String)value[i]; }
        String string(int i) { return utf((Integer)value[i]); }
        int[] pair(int i) { return (int[])value[i]; }
        String[] handle(int i) {
            int[] ref = pair(pair(i)[1]);
            int[] nat = pair(ref[1]);
            return new String[]{utf((Integer)value[ref[0]]), utf(nat[0]), utf(nat[1])};
        }
    }
    static void skipAttributes(DataInputStream in) throws IOException {
        for (int n=in.readUnsignedShort();n>0;n--) {
            in.readUnsignedShort(); in.skipNBytes(in.readInt());
        }
    }
    static List<Class<?>> parameterTypes(String descriptor) {
        List<Class<?>> result=new ArrayList<>();
        for(int pos=1;descriptor.charAt(pos)!=')';) {
            char c=descriptor.charAt(pos++);
            switch(c) {
                case 'L' -> { pos=descriptor.indexOf(';',pos)+1; result.add(Object.class); }
                case '[' -> {
                    while(descriptor.charAt(pos)=='[')pos++;
                    if(descriptor.charAt(pos)=='L') pos=descriptor.indexOf(';',pos)+1; else pos++;
                    result.add(Object.class);
                }
                case 'Z' -> result.add(boolean.class);
                case 'B' -> result.add(byte.class);
                case 'S' -> result.add(short.class);
                case 'C' -> result.add(char.class);
                case 'I' -> result.add(int.class);
                case 'J' -> result.add(long.class);
                case 'F' -> result.add(float.class);
                case 'D' -> result.add(double.class);
                default -> throw new IllegalArgumentException(descriptor);
            }
        }
        return result;
    }
    static Object sample(Class<?> type) {
        if(type==Object.class)return "测试";
        if(type==boolean.class)return true;
        if(type==byte.class)return (byte)1;
        if(type==short.class)return (short)1;
        if(type==char.class)return '星';
        if(type==int.class)return 1;
        if(type==long.class)return 1L;
        if(type==float.class)return 1f;
        if(type==double.class)return 1d;
        throw new IllegalArgumentException(type.toString());
    }
    public static void main(String[] argv) throws Throwable {
        int checked=0, files=0;
        try(ZipFile jar=new ZipFile(argv[0])) {
            var entries=jar.entries();
            while(entries.hasMoreElements()) {
                var entry=entries.nextElement();
                if(!entry.getName().endsWith(".class"))continue;
                try(DataInputStream in=new DataInputStream(jar.getInputStream(entry))) {
                    if(in.readInt()!=0xcafebabe)throw new IOException();
                    in.readInt(); CP cp=new CP(in);
                    in.skipNBytes(6);
                    in.skipNBytes(2L*in.readUnsignedShort());
                    for(int group=0;group<2;group++) {
                        for(int n=in.readUnsignedShort();n>0;n--) {in.skipNBytes(6);skipAttributes(in);}
                    }
                    List<int[]> bsms=new ArrayList<>();
                    for(int n=in.readUnsignedShort();n>0;n--) {
                        String name=cp.utf(in.readUnsignedShort());
                        byte[] data=in.readNBytes(in.readInt());
                        if(name.equals("BootstrapMethods")) {
                            DataInputStream attrs=new DataInputStream(new ByteArrayInputStream(data));
                            for(int b=attrs.readUnsignedShort();b>0;b--) {
                                int ref=attrs.readUnsignedShort(), count=attrs.readUnsignedShort();
                                int[] item=new int[count+1];item[0]=ref;
                                for(int a=1;a<=count;a++)item[a]=attrs.readUnsignedShort();
                                bsms.add(item);
                            }
                        }
                    }
                    int before=checked;
                    for(int i=1;i<cp.tag.length;i++) {
                        if(cp.tag[i]!=18)continue;
                        int[] site=cp.pair(i), bsm=bsms.get(site[0]);
                        String[] handle=cp.handle(bsm[0]);
                        if(!handle[0].equals("java/lang/invoke/StringConcatFactory") || !handle[1].equals("makeConcatWithConstants"))continue;
                        String recipe=cp.string(bsm[1]);
                        if(recipe.codePoints().noneMatch(c -> c>=0x3400 && c<=0x9fff))continue;
                        int[] nat=cp.pair(site[1]);
                        String descriptor=cp.utf(nat[1]);
                        List<Class<?>> types=parameterTypes(descriptor);
                        MethodType methodType=MethodType.methodType(String.class,types);
                        Object[] constants=new Object[bsm.length-2];
                        for(int c=0;c<constants.length;c++) {
                            int ci=bsm[c+2];constants[c]=cp.tag[ci]==8?cp.string(ci):cp.value[ci];
                        }
                        var call=StringConcatFactory.makeConcatWithConstants(MethodHandles.lookup(),"localized",methodType,recipe,constants);
                        List<Object> args=types.stream().map(VerifyAllTextLinkage::sample).toList();
                        String actual=(String)call.getTarget().invokeWithArguments(args);
                        StringBuilder expected=new StringBuilder();int a=0,c=0;
                        for(char ch:recipe.toCharArray()) {
                            if(ch==1)expected.append(args.get(a++));
                            else if(ch==2)expected.append(constants[c++]);
                            else expected.append(ch);
                        }
                        if(!actual.equals(expected.toString()))throw new AssertionError(entry.getName()+" "+i);
                        checked++;
                    }
                    if(checked>before)files++;
                }
            }
        }
        if(checked<0)throw new AssertionError("Too few localized sites: "+checked);
        System.out.println("JVM linked and evaluated "+checked+" localized text call sites in "+files+" classes.");
    }
}
